import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from dotenv import load_dotenv, set_key
from database import init_db, get_db
from shopify_client import build_dashboard_data, clear_cache

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
               "api_dashboard", "api_refresh"]
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
