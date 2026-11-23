import json
import io
from pathlib import Path
from unittest.mock import patch
from config.merchant_rules import MERCHANT_RULES

from app import (
    category_for,
    categorize_descriptions,
    cents,
    db,
    delete_transaction_ids,
    initialize,
    is_expense_transaction,
    money,
    parse_statement_date,
    period_select_options,
    selected_period,
    yearly_totals,
)
from routes.imports import extract_csv_payload, parse_amount

"""
Tests for the application.
"""

def test_money_and_cents():
    assert cents("$1,234.50") == 123450
    assert cents("(12.25)") == 1225
    assert money(-1225) == "-$12.25"


def test_selected_period_supports_historical_months():
    assert selected_period("2026-10") == "2026-10"
    assert selected_period("not-a-month") != "not-a-month"


def test_period_picker_has_month_year_options():
    month_options, year_options = period_select_options("2026-11")
    assert "<option value=11 selected>November</option>" in month_options
    assert "<option value=2026 selected>2026</option>" in year_options
    assert "<option value=2030>2030" in year_options


def test_amex_statement_dates_are_supported():
    assert parse_statement_date("30-Oct-26") == "2026-10-30"
    assert parse_statement_date("2026-10-30") == "2026-10-30"


def test_transaction_edit_supports_split_and_blue_save_button():
    template = Path("templates/edit_transaction.html").read_text()
    script = Path("static/js/edit_transaction.js").read_text()
    assert 'id="transaction-split"' in template
    assert 'id="transaction-amount"' in template
    assert "Save Changes" in template
    assert 'class="blue-action"' in template
    assert "applySplit" in script


def test_dashboard_action_buttons_are_blue_and_palette_is_styled():
    template = Path("templates/dashboard.html").read_text()
    css = Path("static/css/dashboard.css").read_text()
    assert template.count('class="blue-action"') == 3
    assert ".track i.coral" in css
    assert ".track i.violet" in css
    assert ".track i.blue" in css
    assert ".track i.gold" in css
    assert ".track i.mint" in css


def test_dashboard_template_has_csv_dropzone():
    template = Path("templates/dashboard.html").read_text()
    assert 'id="csv-dropzone"' in template
    assert 'accept=".csv,text/csv"' in template


def test_november_csv_formats_are_supported():
    assert parse_statement_date("21-Nov-26") == "2026-11-21"
    assert parse_statement_date("November 21, 2026") == "2026-11-21"
    assert parse_amount("$1,234.50") == 1234.50
    assert parse_amount("(12.25)") == -12.25


def test_multipart_csv_payload_is_extracted():
    boundary = "ledgerboundary"
    raw = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="statement"; filename="november.csv"\r\n'
        "Content-Type: text/csv\r\n\r\n"
        "Date,Description,Amount\r\n21-Nov-26,SHAW CABLESYSTEMS,117.22\r\n"
        f"\r\n--{boundary}--\r\n"
    ).encode()
    payload = extract_csv_payload(raw, f"multipart/form-data; boundary={boundary}")
    assert "SHAW CABLESYSTEMS" in payload
    assert "21-Nov-26" in payload


def test_tangerine_debits_are_expenses_but_credits_are_not():
    assert parse_statement_date("10/18/2026") == "2026-10-18"
    assert is_expense_transaction("DEBIT", "PAYBYPHONE BURNABY", -4.30)
    assert not is_expense_transaction("CREDIT", "PAYMENT - THANK YOU", 75.23)


def test_amex_payment_is_not_an_expense():
    assert not is_expense_transaction("", "PAYMENT RECEIVED - THANK YOU", -432.80)


def test_merchant_rules_are_exported_and_editable():
    assert "shaw" in MERCHANT_RULES["Bills"]
    assert (
        "COCO" in MERCHANT_RULES["Restaurants"]
        or "coco fresh" in MERCHANT_RULES["Restaurants"]
    )


def test_category_rules():
    assert category_for("NETFLIX.COM") == "Entertainment"
    assert category_for("GOODLIFE FITNESS") == "Fitness & gym"
    assert category_for("SAVE-ON-FOODS") == "Groceries"
    assert category_for("SAINT GERMAIN BAKERY") == "Restaurants"
    assert category_for("HAPPY LAMB HOT POT") == "Restaurants"
    assert category_for("BCAA MEMBERSHIP") == "Bills"
    assert category_for("SHAW CABLESYSTEMS") == "Bills"
    assert category_for("COCO FRESH TEA & JUICE") == "Restaurants"
    assert category_for("STARBUCKS CANADA") == "Restaurants"
    assert category_for("RBC INSURANCE") == "Bills"
    assert category_for("AIR CANADA") == "Transport"
    assert category_for("MARRIOTT HOTEL") == "Travel"
    assert category_for("PAYROLL DEPOSIT") == "Income"
    assert category_for("PAYPAL ETRANSFER") == "Cash & transfers"
    assert category_for("SEPHORA") == "Shopping"
    assert category_for("Unknown merchant") == "Other"


def test_local_agent_categories_are_used():
    class Response:
        def read(self):
            return json.dumps({"response": '["Restaurants", "Clothing"]'}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with patch("app.urlopen", return_value=Response()):
        assert categorize_descriptions(["STARBUCKS 123", "ZARA STORE"]) == [
            "Restaurants",
            "Clothing",
        ]


def test_local_agent_falls_back_when_offline():
    with patch("app.urlopen", side_effect=OSError):
        assert categorize_descriptions(["COSTCO"]) == ["Groceries"]


def test_bulk_delete_only_removes_selected_user_transactions(tmp_path, monkeypatch):
    import app

    monkeypatch.setattr(app, "DB_PATH", tmp_path / "ledger.db")
    initialize()
    with db() as con:
        user_id = con.execute(
            "INSERT INTO users(email,password_hash) VALUES('bulk@example.com','hash')"
        ).lastrowid
        first = con.execute(
            "INSERT INTO transactions(user_id,occurred_on,description,amount_cents,category,kind,source) VALUES(?,?,?,?,?,?,?)",
            (user_id, "2026-01-01", "First", 100, "Other", "expense", "manual"),
        ).lastrowid
        second = con.execute(
            "INSERT INTO transactions(user_id,occurred_on,description,amount_cents,category,kind,source) VALUES(?,?,?,?,?,?,?)",
            (user_id, "2026-01-02", "Second", 200, "Other", "expense", "manual"),
        ).lastrowid
        assert delete_transaction_ids(con, user_id, [first]) == 1
        assert (
            con.execute(
                "SELECT id FROM transactions WHERE user_id=?", (user_id,)
            ).fetchone()["id"]
            == second
        )


def test_recurring_entry_can_be_edited_and_deleted(tmp_path, monkeypatch):
    import app

    monkeypatch.setattr(app, "DB_PATH", tmp_path / "ledger.db")
    app.initialize()
    with app.db() as con:
        user_id = con.execute(
            "INSERT INTO users(email,password_hash) VALUES('recurring@example.com','hash')"
        ).lastrowid
        rule_id = con.execute(
            """
            INSERT INTO recurring_rules (
                user_id, description, amount_cents, category, kind,
                day_of_month, next_due
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, "Mortgage", 150000, "Housing", "expense", 1, "2026-12-01"),
        ).lastrowid
        token = app.session(con, user_id)

    edit_payload = (
        b"description=Updated%20Mortgage&amount=1600&category=Housing&"
        b"kind=expense&day=5"
    )
    edit_env = {
        "PATH_INFO": f"/recurring/{rule_id}/edit",
        "REQUEST_METHOD": "POST",
        "wsgi.input": io.BytesIO(edit_payload),
        "CONTENT_LENGTH": str(len(edit_payload)),
        "HTTP_COOKIE": f"expense_session={token}",
    }
    app.app(edit_env, lambda status, headers: None)

    with app.db() as con:
        rule = con.execute(
            "SELECT * FROM recurring_rules WHERE id=?", (rule_id,)
        ).fetchone()
        assert rule["description"] == "Updated Mortgage"
        assert rule["amount_cents"] == 160000
        assert rule["day_of_month"] == 5

    delete_payload = b""
    delete_env = {
        "PATH_INFO": f"/recurring/{rule_id}/delete",
        "REQUEST_METHOD": "POST",
        "wsgi.input": io.BytesIO(delete_payload),
        "CONTENT_LENGTH": "0",
        "HTTP_COOKIE": f"expense_session={token}",
    }
    app.app(delete_env, lambda status, headers: None)

    with app.db() as con:
        assert (
            con.execute(
                "SELECT * FROM recurring_rules WHERE id=?", (rule_id,)
            ).fetchone()
            is None
        )


def test_yearly_totals_use_selected_year(tmp_path, monkeypatch):
    import app

    monkeypatch.setattr(app, "DB_PATH", tmp_path / "ledger.db")
    initialize()
    with db() as con:
        user_id = con.execute(
            "INSERT INTO users(email,password_hash) VALUES('year@example.com','hash')"
        ).lastrowid
        con.execute(
            "INSERT INTO transactions(user_id,occurred_on,description,amount_cents,category,kind,source) VALUES(?,?,?,?,?,?,?)",
            (user_id, "2025-12-01", "Old income", 50000, "Income", "income", "manual"),
        )
        con.execute(
            "INSERT INTO transactions(user_id,occurred_on,description,amount_cents,category,kind,source) VALUES(?,?,?,?,?,?,?)",
            (user_id, "2026-01-01", "New income", 100000, "Income", "income", "manual"),
        )
        con.execute(
            "INSERT INTO transactions(user_id,occurred_on,description,amount_cents,category,kind,source) VALUES(?,?,?,?,?,?,?)",
            (user_id, "2026-02-01", "New expense", 40000, "Bills", "expense", "manual"),
        )
        income, expenses = yearly_totals(con, user_id, "2026")
        assert income == 100000
        assert expenses == 40000


def test_delete_selected_route_removes_checked_transactions(tmp_path, monkeypatch):
    import app, io

    monkeypatch.setattr(app, "DB_PATH", tmp_path / "ledger.db")
    app.initialize()
    with app.db() as con:
        user_id = con.execute(
            "INSERT INTO users(email,password_hash) VALUES('delete@example.com','hash')"
        ).lastrowid
        first = con.execute(
            "INSERT INTO transactions(user_id,occurred_on,description,amount_cents,category,kind,source) VALUES(?,?,?,?,?,?,?)",
            (user_id, "2026-01-01", "First", 100, "Other", "expense", "manual"),
        ).lastrowid
        second = con.execute(
            "INSERT INTO transactions(user_id,occurred_on,description,amount_cents,category,kind,source) VALUES(?,?,?,?,?,?,?)",
            (user_id, "2026-01-02", "Second", 200, "Other", "expense", "manual"),
        ).lastrowid
        token = app.session(con, user_id)
    payload = f"transaction_ids={first}&transaction_ids={second}".encode()
    env = {
        "PATH_INFO": "/transactions/delete-selected",
        "REQUEST_METHOD": "POST",
        "wsgi.input": io.BytesIO(payload),
        "CONTENT_LENGTH": str(len(payload)),
        "HTTP_COOKIE": f"expense_session={token}",
    }
    response = []
    app.app(env, lambda status, headers: response.append((status, headers)))
    with app.db() as con:
        assert (
            con.execute(
                "SELECT COUNT(*) FROM transactions WHERE user_id=?", (user_id,)
            ).fetchone()[0]
            == 0
        )


def test_database_initializes(tmp_path, monkeypatch):
    import app

    monkeypatch.setattr(app, "DB_PATH", tmp_path / "ledger.db")
    initialize()
    with db() as con:
        assert (
            con.execute("SELECT name FROM sqlite_master WHERE name='users'").fetchone()[
                0
            ]
            == "users"
        )


def test_transaction_can_be_updated_and_deleted(tmp_path, monkeypatch):
    import app

    monkeypatch.setattr(app, "DB_PATH", tmp_path / "ledger.db")
    initialize()
    with db() as con:
        user_id = con.execute(
            "INSERT INTO users(email,password_hash) VALUES('me@example.com','hash')"
        ).lastrowid
        transaction_id = con.execute(
            "INSERT INTO transactions(user_id,occurred_on,description,amount_cents,category,kind,source) VALUES(?,?,?,?,?,?,?)",
            (
                user_id,
                "2026-01-01",
                "Wrong merchant",
                1000,
                "Other",
                "expense",
                "card import",
            ),
        ).lastrowid
        con.execute(
            "UPDATE transactions SET description=?,category=? WHERE id=? AND user_id=?",
            ("Correct merchant", "Groceries", transaction_id, user_id),
        )
        assert (
            con.execute(
                "SELECT category FROM transactions WHERE id=?", (transaction_id,)
            ).fetchone()["category"]
            == "Groceries"
        )
        con.execute(
            "DELETE FROM transactions WHERE id=? AND user_id=?",
            (transaction_id, user_id),
        )
        assert (
            con.execute(
                "SELECT * FROM transactions WHERE id=?", (transaction_id,)
            ).fetchone()
            is None
        )
