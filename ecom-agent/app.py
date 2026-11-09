import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from dotenv import load_dotenv, set_key
from database import init_db, get_db
from shopify_client import build_dashboard_data, clear_cache, get_orders, get_products, get_order

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")


def get_stores():
    db = get_db()
    stores = db.execute("SELECT * FROM stores ORDER BY name").fetchall()
    db.close()
    return stores


def api_key_configured():
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


@app.before_request
def check_api_key():
    allowed = ["settings", "save_api_key", "add_store", "delete_store",
               "edit_store", "toggle_dark_mode", "set_store", "static",
               "api_dashboard", "api_refresh", "api_orders",
               "api_order_detail", "api_products"]
    if request.endpoint not in allowed and not api_key_configured():
        flash("Du behöver ange din Anthropic API-nyckel först.", "error")
        return redirect(url_for("settings"))


@app.context_processor
def inject_globals():
    return {"stores": get_stores(), "active_page": request.endpoint or ""}


@app.route("/")
def dashboard():
    store_id = session.get("active_store")
    stores = get_stores()
    if stores and not store_id:
        store_id = stores[0]["id"]
        session["active_store"] = store_id
    return render_template("dashboard.html", active_store_id=store_id)


@app.route("/api/dashboard/<int:store_id>")
def api_dashboard(store_id):
    try:
        data = build_dashboard_data(store_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/refresh/<int:store_id>", methods=["POST"])
def api_refresh(store_id):
    clear_cache(store_id)
    try:
        data = build_dashboard_data(store_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/orders")
def orders():
    store_id = session.get("active_store")
    stores = get_stores()
    if stores and not store_id:
        store_id = stores[0]["id"]
        session["active_store"] = store_id
    return render_template("orders.html", active_store_id=store_id)


@app.route("/api/orders/<int:store_id>")
def api_orders(store_id):
    try:
        raw = get_orders(store_id, days=90, status="any")
        orders_list = []
        for o in raw:
            customer = o.get("customer") or {}
            cname = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or "Gäst"
            items = []
            for li in o.get("line_items", []):
                items.append({
                    "title": li.get("title", ""),
                    "quantity": li.get("quantity", 1),
                    "price": li.get("price", "0.00"),
                    "sku": li.get("sku", ""),
                    "image": (li.get("image") or {}).get("src", ""),
                })
            shipping = o.get("shipping_address") or {}
            orders_list.append({
                "id": o.get("id"),
                "order_number": o.get("order_number", o.get("id")),
                "created_at": o.get("created_at", ""),
                "customer": cname,
                "email": (o.get("customer") or {}).get("email", ""),
                "items": items,
                "items_summary": ", ".join(i["title"] for i in items[:3]) + (f" (+{len(items)-3})" if len(items) > 3 else ""),
                "total": o.get("total_price", "0.00"),
                "currency": o.get("currency", "SEK"),
                "fulfillment": o.get("fulfillment_status") or "unfulfilled",
                "financial": o.get("financial_status", "pending"),
                "gateway": o.get("gateway", ""),
                "shipping_name": f"{shipping.get('first_name', '')} {shipping.get('last_name', '')}".strip(),
                "shipping_address": ", ".join(filter(None, [
                    shipping.get("address1", ""),
                    shipping.get("zip", ""),
                    shipping.get("city", ""),
                    shipping.get("country", ""),
                ])),
            })
        return jsonify(orders_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/order/<int:store_id>/<int:order_id>")
def api_order_detail(store_id, order_id):
    try:
        data = get_order(store_id, order_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/products")
def products():
    store_id = session.get("active_store")
    stores = get_stores()
    if stores and not store_id:
        store_id = stores[0]["id"]
        session["active_store"] = store_id
    return render_template("products.html", active_store_id=store_id)


@app.route("/api/products/<int:store_id>")
def api_products(store_id):
    try:
        raw = get_products(store_id)
        products_list = []
        for p in raw:
            total_inv = 0
            price_min = None
            for v in p.get("variants", []):
                inv = v.get("inventory_quantity") or 0
                total_inv += inv
                vp = float(v.get("price", 0))
                if price_min is None or vp < price_min:
                    price_min = vp
            img = ""
            if p.get("image"):
                img = p["image"].get("src", "")
            elif p.get("images"):
                img = p["images"][0].get("src", "")
            products_list.append({
                "id": p.get("id"),
                "title": p.get("title", ""),
                "image": img,
                "price": price_min or 0,
                "inventory": total_inv,
                "status": p.get("status", "active"),
                "vendor": p.get("vendor", ""),
                "product_type": p.get("product_type", ""),
                "variants_count": len(p.get("variants", [])),
            })
        return jsonify(products_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/settings")
def settings():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    return render_template("settings.html", api_key=api_key)


@app.route("/save-api-key", methods=["POST"])
def save_api_key():
    key = request.form.get("api_key", "").strip()
    if not key:
        flash("API-nyckeln kan inte vara tom.", "error")
        return redirect(url_for("settings"))

    if not os.path.exists(ENV_PATH):
        with open(ENV_PATH, "w") as f:
            f.write("")

    set_key(ENV_PATH, "ANTHROPIC_API_KEY", key)
    os.environ["ANTHROPIC_API_KEY"] = key
    flash("API-nyckel sparad.", "success")
    return redirect(url_for("settings"))


@app.route("/add-store", methods=["POST"])
def add_store():
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    token = request.form.get("shopify_token", "").strip()

    if not all([name, url, token]):
        flash("Alla fält måste fyllas i.", "error")
        return redirect(url_for("settings"))

    db = get_db()
    db.execute(
        "INSERT INTO stores (name, url, shopify_token) VALUES (?, ?, ?)",
        (name, url, token),
    )
    db.commit()
    db.close()
    flash(f"Butik '{name}' tillagd.", "success")
    return redirect(url_for("settings"))


@app.route("/edit-store/<int:store_id>", methods=["POST"])
def edit_store(store_id):
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    token = request.form.get("shopify_token", "").strip()

    if not all([name, url, token]):
        flash("Alla fält måste fyllas i.", "error")
        return redirect(url_for("settings"))

    db = get_db()
    db.execute(
        "UPDATE stores SET name=?, url=?, shopify_token=? WHERE id=?",
        (name, url, token, store_id),
    )
    db.commit()
    db.close()
    flash(f"Butik '{name}' uppdaterad.", "success")
    return redirect(url_for("settings"))


@app.route("/delete-store/<int:store_id>", methods=["POST"])
def delete_store(store_id):
    db = get_db()
    db.execute("DELETE FROM stores WHERE id=?", (store_id,))
    db.commit()
    db.close()
    if session.get("active_store") == store_id:
        session.pop("active_store", None)
    flash("Butik borttagen.", "success")
    return redirect(url_for("settings"))


@app.route("/set-store/<int:store_id>", methods=["POST"])
def set_store(store_id):
    session["active_store"] = store_id
    return "", 204


@app.route("/toggle-dark-mode", methods=["POST"])
def toggle_dark_mode():
    session["light_mode"] = not session.get("light_mode", False)
    return "", 204


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
