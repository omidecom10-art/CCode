import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from dotenv import load_dotenv, set_key
from database import init_db, get_db
from shopify_client import build_dashboard_data, clear_cache, get_orders, get_products, get_order
from ai_agent import EcomAgent
from calculators import margin_calculator, pricing_suggestion
import anthropic

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

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
               "api_order_detail", "api_products",
               "chat", "api_chat", "api_chat_history", "api_chat_conversations",
               "api_chat_clear",
               "projects_page", "project_detail", "api_projects_list",
               "api_projects_create", "api_project_update", "api_project_delete",
               "api_project_tasks_create", "api_task_update", "api_task_delete",
               "tools_page", "api_tools_swot", "api_tools_copy"]
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


@app.route("/projects")
def projects_page():
    return render_template("projects.html")


@app.route("/projects/<int:project_id>")
def project_detail(project_id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    db.close()
    if not project:
        flash("Projektet hittades inte.", "error")
        return redirect(url_for("projects_page"))
    return render_template("project_detail.html", project=project)


@app.route("/api/projects", methods=["GET"])
def api_projects_list():
    db = get_db()
    rows = db.execute("""
        SELECT p.*,
            (SELECT COUNT(*) FROM tasks WHERE project_id=p.id) AS tasks_total,
            (SELECT COUNT(*) FROM tasks WHERE project_id=p.id AND done=1) AS tasks_done
        FROM projects p ORDER BY p.created_at DESC
    """).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/projects", methods=["POST"])
def api_projects_create():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Namn krävs."}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO projects (name, description, status, budget, deadline, store_id) VALUES (?,?,?,?,?,?)",
        (
            name,
            data.get("description", ""),
            data.get("status", "ide"),
            data.get("budget"),
            data.get("deadline"),
            data.get("store_id"),
        ),
    )
    db.commit()
    pid = cur.lastrowid
    db.close()
    return jsonify({"id": pid}), 201


@app.route("/api/projects/<int:project_id>", methods=["GET"])
def api_project_get(project_id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not project:
        db.close()
        return jsonify({"error": "Ej hittat."}), 404
    tasks = db.execute(
        "SELECT id, text, done, created_at FROM tasks WHERE project_id=? ORDER BY created_at",
        (project_id,),
    ).fetchall()
    db.close()
    result = dict(project)
    result["tasks"] = [dict(t) for t in tasks]
    return jsonify(result)


@app.route("/api/projects/<int:project_id>", methods=["PATCH"])
def api_project_update(project_id):
    data = request.get_json() or {}
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not project:
        db.close()
        return jsonify({"error": "Ej hittat."}), 404

    fields = {}
    for key in ("name", "description", "status", "budget", "deadline", "notes"):
        if key in data:
            fields[key] = data[key]

    if fields:
        set_clause = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values()) + [project_id]
        db.execute(f"UPDATE projects SET {set_clause} WHERE id=?", values)
        db.commit()

    db.close()
    return "", 204


@app.route("/api/projects/<int:project_id>", methods=["DELETE"])
def api_project_delete(project_id):
    db = get_db()
    db.execute("DELETE FROM projects WHERE id=?", (project_id,))
    db.commit()
    db.close()
    return "", 204


@app.route("/api/projects/<int:project_id>/tasks", methods=["POST"])
def api_project_tasks_create(project_id):
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Text krävs."}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO tasks (project_id, text) VALUES (?,?)",
        (project_id, text),
    )
    db.commit()
    tid = cur.lastrowid
    db.close()
    return jsonify({"id": tid}), 201


@app.route("/api/tasks/<int:task_id>", methods=["PATCH"])
def api_task_update(task_id):
    data = request.get_json() or {}
    db = get_db()
    if "done" in data:
        db.execute("UPDATE tasks SET done=? WHERE id=?", (1 if data["done"] else 0, task_id))
    if "text" in data:
        db.execute("UPDATE tasks SET text=? WHERE id=?", (data["text"], task_id))
    db.commit()
    db.close()
    return "", 204


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def api_task_delete(task_id):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    db.commit()
    db.close()
    return "", 204


@app.route("/chat")
def chat():
    store_id = session.get("active_store")
    channel = str(store_id) if store_id else "null"
    return render_template("chat.html", active_channel=channel)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    store_id_raw = data.get("store_id")

    if not message:
        return jsonify({"error": "Meddelandet kan inte vara tomt."}), 400

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Anthropic API-nyckel saknas. Gå till inställningar."}), 400

    store_id = None
    if store_id_raw is not None and store_id_raw != "null" and store_id_raw != "":
        try:
            store_id = int(store_id_raw)
        except (ValueError, TypeError):
            pass

    try:
        agent = EcomAgent(store_id, api_key)
        reply = agent.chat(message)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/history/<store_id>")
def api_chat_history(store_id):
    sid = None if store_id == "null" else int(store_id)
    messages = EcomAgent.get_history(sid)
    return jsonify(messages)


@app.route("/api/chat/conversations")
def api_chat_conversations():
    convos = EcomAgent.get_conversations()
    stores_map = {s["id"]: s["name"] for s in get_stores()}
    for c in convos:
        c["store_name"] = stores_map.get(c["store_id"], "Generell") if c["store_id"] else "Generell"
    return jsonify(convos)


@app.route("/api/chat/clear/<store_id>", methods=["POST"])
def api_chat_clear(store_id):
    EcomAgent.clear_history(store_id if store_id == "null" else store_id)
    return "", 204


@app.route("/tools")
def tools_page():
    return render_template("tools.html")


@app.route("/api/tools/swot", methods=["POST"])
def api_tools_swot():
    data = request.get_json() or {}
    description = data.get("description", "").strip()
    if not description:
        return jsonify({"error": "Beskrivning krävs."}), 400

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Anthropic API-nyckel saknas."}), 400

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system="Du är en e-handelsanalytiker. Svara ALLTID med exakt denna JSON-struktur, inget annat: {\"strengths\": [...], \"weaknesses\": [...], \"opportunities\": [...], \"threats\": [...]}. Varje array ska ha 3-5 korta punkter på svenska.",
            messages=[{"role": "user", "content": f"Gör en SWOT-analys för: {description}"}],
        )
        import json
        text = resp.content[0].text.strip()
        result = json.loads(text)
        return jsonify(result)
    except json.JSONDecodeError:
        return jsonify({"error": "Kunde inte tolka AI-svaret. Försök igen."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools/copy", methods=["POST"])
def api_tools_copy():
    data = request.get_json() or {}
    context = data.get("context", "").strip()
    copy_type = data.get("type", "produktbeskrivning")
    audience = data.get("audience", "")
    tone = data.get("tone", "professionell")

    if not context:
        return jsonify({"error": "Kontext krävs."}), 400

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Anthropic API-nyckel saknas."}), 400

    prompt = f"""Skriv en {copy_type} på svenska.

Produkt/Kontext: {context}
Målgrupp: {audience or 'Ej specificerad'}
Ton: {tone}

Ge ett färdigt, publiceringsklart resultat. Använd markdown-formatering."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system="Du är en expert på e-handelscopywriting på svenska. Skriv säljande, engagerande text.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text
        return jsonify({"text": text})
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


init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
