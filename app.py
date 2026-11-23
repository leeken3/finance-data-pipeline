"""Ledger WSGI application entry point."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.parse import parse_qs
from urllib.request import urlopen
from wsgiref.simple_server import make_server

from config.settings import CATEGORIES, DB_PATH as DEFAULT_DB_PATH
from database import db as open_db, initialize as initialize_database
from routes.auth import handle_auth
from routes.dashboard import handle_dashboard
from routes.http import redirect, not_found
from routes.imports import handle_import
from routes.static import handle_static
from routes.transactions import (
    handle_history,
    handle_recurring_action,
    handle_recurring_history,
    handle_transaction_action,
)
from services.auth import (
    current_user as find_current_user,
    password_hash,
    password_matches,
    session,
)
from services.categories import category_for, categorize_descriptions as categorize
from services.transactions import (
    delete_transaction_ids,
    is_expense_transaction,
    yearly_totals,
)
from utils.dates import parse_statement_date, selected_period
from utils.formatting import cents, cookies, form, form_values, money

ROOT = Path(__file__).resolve().parent
DB_PATH = DEFAULT_DB_PATH


def db():
    """
    Return an application SQLite connection.

    :return: SQLite connection
    """
    return open_db(DB_PATH)


def initialize():
    """
    Create the database schema when the application starts.

    :return: None
    """
    initialize_database(DB_PATH)


def categorize_descriptions(descriptions, user_id=None):
    """
    Compatibility wrapper for categorization tests and routes.

    :param descriptions: List of transaction descriptions
    :param user_id: Optional user ID for categorization context
    :return: Categorized descriptions
    """
    return categorize(descriptions, user_id, db, urlopen)


def period_select_options(selected: str) -> tuple[str, str]:
    """
    Return month and year option HTML for compatibility callers.

    :param selected: The selected date in the format 'YYYY-MM'
    :return: A tuple of month and year option HTML
    """
    from datetime import datetime

    year = int(selected[:4])
    month = int(selected[5:7])
    month_options = "".join(
        f"<option value={number:02d}{' selected' if number == month else ''}>{datetime(2000,number,1).strftime('%B')}</option>"
        for number in range(1, 13)
    )
    year_options = "".join(
        f"<option value={number}{' selected' if number == year else ''}>{number}</option>"
        for number in range(2000, date.today().year + 26)
    )
    return month_options, year_options


def dashboard(user, period=None, notice=None):
    """
    Render the dashboard via the dashboard route module.

    :param user: The current user
    :param period: The selected period
    :param notice: An optional notice to display
    :return: The rendered dashboard
    """
    env = {"QUERY_STRING": ""}
    if period:
        env["QUERY_STRING"] = f"month={period}"

    def capture(status, headers):
        pass

    return handle_dashboard(env, capture, db, user, notice)[0]


def app(env, start):
    """
    Dispatch WSGI requests to focused route modules.

    :param env: WSGI environment
    :param start: WSGI start_response callable
    :return: WSGI response iterable
    """
    initialize()
    path = env["PATH_INFO"]
    method = env["REQUEST_METHOD"]

    if path.startswith("/static/"):
        return handle_static(path, start)

    user = find_current_user(env, db)
    if path == "/logout":
        start(
            "303 See Other",
            [
                ("Location", "/login"),
                (
                    "Set-Cookie",
                    "expense_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax",
                ),
            ],
        )
        return [b""]
    if not user and path not in ("/login", "/register"):
        return redirect(start, "/login")

    if path in ("/login", "/register"):
        return handle_auth(path, method, env, start, db)

    if path == "/" and method == "GET":
        return handle_dashboard(
            env,
            start,
            db,
            user,
            parse_qs(env.get("QUERY_STRING", "")).get("notice", [None])[0],
        )

    if path == "/transaction" and method == "POST":
        values = form(env)
        try:
            with db() as con:
                con.execute(
                    """
                    INSERT INTO transactions (
                        user_id, occurred_on, description, amount_cents,
                        category, kind, source
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user["id"],
                        values["occurred_on"],
                        values["description"].strip(),
                        cents(values["amount"]),
                        values["category"],
                        values["kind"],
                        "manual",
                    ),
                )
        except (KeyError, ValueError):
            pass
        return redirect(start, "/")

    if path == "/recurring" and method == "POST":
        values = form(env)
        day = int(values["day"])
        today = date.today()
        due = date(today.year, today.month, day)
        if due < today:
            due = date(today.year + (today.month == 12), today.month % 12 + 1, day)
        with db() as con:
            con.execute(
                """
                INSERT INTO recurring_rules (
                    user_id, description, amount_cents, category,
                    kind, day_of_month, next_due
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    values["description"].strip(),
                    cents(values["amount"]),
                    values["category"],
                    values["kind"],
                    day,
                    due.isoformat(),
                ),
            )
        return redirect(start, "/")

    if path == "/import" and method == "POST":
        return handle_import(env, start, db, user, categorize_descriptions)

    if path == "/transactions/recurring" and method == "GET":
        return handle_recurring_history(env, start, db, user)

    if path.startswith("/recurring/"):
        return handle_recurring_action(path, method, env, start, db, user)

    if path == "/transactions/delete-selected" and method == "POST":
        return handle_transaction_action(path, method, env, start, db, user)

    if path.startswith("/transactions/"):
        return handle_transaction_action(path, method, env, start, db, user)

    if path == "/transactions":
        return handle_history(env, start, db, user)

    return not_found(start)

"""
Main application entry point.
"""
if __name__ == "__main__":
    initialize()
    print("Ledger running at http://127.0.0.1:8000")
    make_server("127.0.0.1", 8000, app).serve_forever()
