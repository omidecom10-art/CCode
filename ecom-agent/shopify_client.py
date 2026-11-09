import json
import time
import requests
from datetime import datetime, timedelta, timezone
from database import get_db

CACHE_MAX_AGE = 300


def _get_store(store_id):
    db = get_db()
    store = db.execute("SELECT * FROM stores WHERE id=?", (store_id,)).fetchone()
    db.close()
    if not store:
        raise ValueError(f"Butik med id {store_id} hittades inte")
    return store


def _api_url(store_url, endpoint):
    url = store_url.rstrip("/")
    if not url.startswith("https://"):
        url = "https://" + url
    return f"{url}/admin/api/2024-01/{endpoint}.json"


def _get_cached(store_id, cache_key):
    db = get_db()
    row = db.execute(
        "SELECT data, cached_at FROM api_cache WHERE store_id=? AND cache_key=?",
        (store_id, cache_key),
    ).fetchone()
    db.close()
    if row:
        cached_at = datetime.fromisoformat(row["cached_at"])
        age = (datetime.now(timezone.utc) - cached_at.replace(tzinfo=timezone.utc)).total_seconds()
        if age < CACHE_MAX_AGE:
            return json.loads(row["data"])
    return None


def _set_cache(store_id, cache_key, data):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """INSERT INTO api_cache (store_id, cache_key, data, cached_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(store_id, cache_key)
           DO UPDATE SET data=excluded.data, cached_at=excluded.cached_at""",
        (store_id, cache_key, json.dumps(data), now),
    )
    db.commit()
    db.close()


def clear_cache(store_id):
    db = get_db()
    db.execute("DELETE FROM api_cache WHERE store_id=?", (store_id,))
    db.commit()
    db.close()


def _shopify_get(store, endpoint, params=None):
    url = _api_url(store["url"], endpoint)
    headers = {"X-Shopify-Access-Token": store["shopify_token"]}
    max_retries = 3
    for attempt in range(max_retries):
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", 2))
            time.sleep(retry_after)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return resp.json()


def _paginated_get(store, endpoint, resource_key, params=None):
    if params is None:
        params = {}
    params.setdefault("limit", 250)
    all_items = []
    url = _api_url(store["url"], endpoint)
    headers = {"X-Shopify-Access-Token": store["shopify_token"]}

    while url:
        max_retries = 3
        resp = None
        for attempt in range(max_retries):
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", 2))
                time.sleep(retry_after)
                continue
            resp.raise_for_status()
            break
        else:
            resp.raise_for_status()

        data = resp.json()
        all_items.extend(data.get(resource_key, []))

        url = None
        params = None
        link_header = resp.headers.get("Link", "")
        if 'rel="next"' in link_header:
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    url = part.split("<")[1].split(">")[0]
                    break
    return all_items


def get_orders(store_id, days=30, status="any"):
    cache_key = f"orders_{days}_{status}"
    cached = _get_cached(store_id, cache_key)
    if cached is not None:
        return cached

    store = _get_store(store_id)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    params = {
        "status": status,
        "created_at_min": since,
        "limit": 250,
    }
    orders = _paginated_get(store, "orders", "orders", params)
    _set_cache(store_id, cache_key, orders)
    return orders


def get_products(store_id):
    cache_key = "products"
    cached = _get_cached(store_id, cache_key)
    if cached is not None:
        return cached

    store = _get_store(store_id)
    products = _paginated_get(store, "products", "products", {"limit": 250})
    _set_cache(store_id, cache_key, products)
    return products


def get_order(store_id, order_id):
    cache_key = f"order_{order_id}"
    cached = _get_cached(store_id, cache_key)
    if cached is not None:
        return cached

    store = _get_store(store_id)
    data = _shopify_get(store, f"orders/{order_id}")
    order = data.get("order", {})
    _set_cache(store_id, cache_key, order)
    return order


def build_dashboard_data(store_id):
    orders = get_orders(store_id, days=30, status="any")
    products = get_products(store_id)

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    revenue_today = 0.0
    revenue_week = 0.0
    revenue_month = 0.0
    total_orders = 0
    total_revenue = 0.0

    status_counts = {"unfulfilled": 0, "fulfilled": 0, "refunded": 0}
    product_revenue = {}
    daily_revenue = {}
    daily_orders = {}

    for order in orders:
        created = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00"))
        price = float(order.get("total_price", 0))
        financial = order.get("financial_status", "")

        if financial == "refunded":
            status_counts["refunded"] += 1
        elif order.get("fulfillment_status") == "fulfilled":
            status_counts["fulfilled"] += 1
        else:
            status_counts["unfulfilled"] += 1

        if financial != "refunded":
            total_orders += 1
            total_revenue += price

            if created >= today_start:
                revenue_today += price
            if created >= week_start:
                revenue_week += price
            if created >= month_start:
                revenue_month += price

        day_key = created.strftime("%Y-%m-%d")
        daily_revenue[day_key] = daily_revenue.get(day_key, 0) + price
        daily_orders[day_key] = daily_orders.get(day_key, 0) + 1

        for item in order.get("line_items", []):
            pid = item.get("product_id")
            pname = item.get("title", "Okänd")
            item_rev = float(item.get("price", 0)) * item.get("quantity", 1)
            if pid:
                if pid not in product_revenue:
                    product_revenue[pid] = {"name": pname, "revenue": 0}
                product_revenue[pid]["revenue"] += item_rev

    avg_order = total_revenue / total_orders if total_orders else 0

    top_products = sorted(product_revenue.values(), key=lambda x: x["revenue"], reverse=True)[:5]

    low_stock = []
    for product in products:
        for variant in product.get("variants", []):
            inv = variant.get("inventory_quantity", 0)
            if inv is not None and inv < 5:
                low_stock.append({
                    "product": product.get("title", "Okänd"),
                    "variant": variant.get("title", "Standard"),
                    "sku": variant.get("sku", ""),
                    "quantity": inv,
                })

    chart_labels = []
    chart_revenue = []
    chart_orders = []
    for i in range(29, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        chart_labels.append(day)
        chart_revenue.append(round(daily_revenue.get(day, 0), 2))
        chart_orders.append(daily_orders.get(day, 0))

    recent_orders = []
    sorted_orders = sorted(orders, key=lambda o: o["created_at"], reverse=True)[:20]
    for order in sorted_orders:
        items = ", ".join(i["title"] for i in order.get("line_items", [])[:3])
        if len(order.get("line_items", [])) > 3:
            items += f" (+{len(order['line_items']) - 3})"
        customer = order.get("customer", {})
        if customer:
            cname = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        else:
            cname = "Gäst"
        recent_orders.append({
            "id": order.get("order_number", order.get("id")),
            "date": datetime.fromisoformat(
                order["created_at"].replace("Z", "+00:00")
            ).strftime("%Y-%m-%d %H:%M"),
            "customer": cname,
            "items": items,
            "total": order.get("total_price", "0.00"),
            "currency": order.get("currency", "SEK"),
            "fulfillment": order.get("fulfillment_status") or "unfulfilled",
            "financial": order.get("financial_status", "pending"),
        })

    return {
        "kpi": {
            "revenue_today": round(revenue_today, 2),
            "revenue_week": round(revenue_week, 2),
            "revenue_month": round(revenue_month, 2),
            "total_orders": total_orders,
            "avg_order": round(avg_order, 2),
        },
        "status": status_counts,
        "top_products": top_products,
        "low_stock": low_stock,
        "recent_orders": recent_orders,
        "chart": {
            "labels": chart_labels,
            "revenue": chart_revenue,
            "orders": chart_orders,
        },
    }
