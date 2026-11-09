import os
import json
from anthropic import Anthropic
from database import get_db
from shopify_client import build_dashboard_data


SYSTEM_PROMPT = """Du är en e-handelsexpert och AI-assistent för Ecom Agent.
Du hjälper butiksägare att analysera sin Shopify-butik, ge råd om försäljning,
marknadsföring, lagerhantering och kundupplevelse.

Svara alltid på svenska. Var koncis men grundlig. Använd data från butiken
när det finns tillgängligt. Formatera gärna svar med markdown: fetstil,
listor, tabeller och kodblock vid behov.

Om du inte har specifik butiksdata, ge generella e-handelsråd baserat
på best practices."""


def _get_store_context(store_id):
    try:
        data = build_dashboard_data(store_id)
    except Exception:
        return ""

    kpi = data.get("kpi", {})
    top = data.get("top_products", [])
    status = data.get("status", {})
    low_stock = data.get("low_stock", [])

    lines = [
        "--- Aktuell butiksdata ---",
        f"Intäkter idag: {kpi.get('revenue_today', 0)} kr",
        f"Intäkter denna vecka: {kpi.get('revenue_week', 0)} kr",
        f"Intäkter denna månad: {kpi.get('revenue_month', 0)} kr",
        f"Totalt antal ordrar (30d): {kpi.get('total_orders', 0)}",
        f"Genomsnittligt ordervärde: {kpi.get('avg_order', 0)} kr",
        f"Ej uppfyllda: {status.get('unfulfilled', 0)}, Uppfyllda: {status.get('fulfilled', 0)}, Återbetalda: {status.get('refunded', 0)}",
    ]

    if top:
        lines.append("\nTopp 5 produkter (intäkt):")
        for i, p in enumerate(top[:5], 1):
            lines.append(f"  {i}. {p['name']} — {p['revenue']} kr")

    if low_stock:
        lines.append("\nLågt lager:")
        for item in low_stock[:10]:
            lines.append(f"  - {item['product']} ({item['variant']}): {item['quantity']} st")

    return "\n".join(lines)


class EcomAgent:
    def __init__(self, store_id, anthropic_key):
        self.store_id = store_id
        self.client = Anthropic(api_key=anthropic_key)

    def _load_history(self):
        db = get_db()
        rows = db.execute(
            "SELECT role, content FROM chat_history WHERE store_id IS ? ORDER BY id",
            (self.store_id,),
        ).fetchall()
        db.close()
        return [{"role": r["role"], "content": r["content"]} for r in rows]

    def _save_message(self, role, content):
        db = get_db()
        db.execute(
            "INSERT INTO chat_history (store_id, role, content) VALUES (?, ?, ?)",
            (self.store_id, role, content),
        )
        db.commit()
        db.close()

    def chat(self, user_message):
        history = self._load_history()

        system = SYSTEM_PROMPT
        if self.store_id is not None:
            ctx = _get_store_context(self.store_id)
            if ctx:
                system += "\n\n" + ctx

        history.append({"role": "user", "content": user_message})
        self._save_message("user", user_message)

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            messages=history,
        )

        reply = response.content[0].text
        self._save_message("assistant", reply)
        return reply

    @staticmethod
    def get_conversations():
        db = get_db()
        rows = db.execute("""
            SELECT store_id,
                   MIN(id) AS first_id,
                   MAX(created_at) AS last_at,
                   COUNT(*) AS msg_count
            FROM chat_history
            GROUP BY store_id
            ORDER BY MAX(id) DESC
        """).fetchall()
        db.close()
        return [dict(r) for r in rows]

    @staticmethod
    def clear_history(store_id):
        db = get_db()
        if store_id == "null":
            db.execute("DELETE FROM chat_history WHERE store_id IS NULL")
        else:
            db.execute("DELETE FROM chat_history WHERE store_id = ?", (store_id,))
        db.commit()
        db.close()

    @staticmethod
    def get_history(store_id):
        db = get_db()
        if store_id is None:
            rows = db.execute(
                "SELECT role, content, created_at FROM chat_history WHERE store_id IS NULL ORDER BY id"
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT role, content, created_at FROM chat_history WHERE store_id = ? ORDER BY id",
                (store_id,),
            ).fetchall()
        db.close()
        return [dict(r) for r in rows]
