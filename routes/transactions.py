"""Transaction history, edit, and deletion routes."""

from datetime import date
from html import escape
from urllib.parse import parse_qs, quote_plus

from config.settings import CATEGORIES
from routes.http import redirect, not_found
from services.transactions import delete_transaction_ids
from templates.views import page, render_fragment, render_template
from utils.formatting import cents, form, form_values, money


def handle_transaction_action(path: str, method: str, env: dict, start, db, user):
    """
    Handle individual edit/delete routes and bulk deletion.

    :param path: The request path.
    :param method: The HTTP method (e.g., "GET", "POST").
    :param env: The WSGI environment dictionary.
    :param start: The WSGI start_response callable.
    :param db: The database connection.
    :param user: The user information.
    :return: A WSGI response.
    """
    if path == "/transactions/delete-selected" and method == "POST":
        values = form_values(env)
        ids = [
            int(value) for value in values.get("transaction_ids", []) if value.isdigit()
        ]
        if ids:
            with db() as con:
                delete_transaction_ids(con, user["id"], ids)
        return redirect(start, "/transactions")

    parts = path.strip("/").split("/")
    if len(parts) != 3 or not parts[1].isdigit() or parts[2] not in ("edit", "delete"):
        return not_found(start)
    transaction_id = int(parts[1])
    with db() as con:
        transaction = con.execute(
            "SELECT * FROM transactions WHERE id=? AND user_id=?",
            (transaction_id, user["id"]),
        ).fetchone()
        if not transaction:
            return not_found(start)
        if parts[2] == "delete" and method == "POST":
            con.execute(
                "DELETE FROM transactions WHERE id=? AND user_id=?",
                (transaction_id, user["id"]),
            )
            return redirect(start, "/transactions")
        if parts[2] == "edit" and method == "POST":
            values = form(env)
            try:
                con.execute(
                    """
                    UPDATE transactions
                    SET occurred_on=?, description=?, amount_cents=?,
                        category=?, kind=?
                    WHERE id=? AND user_id=?
                    """,
                    (
                        values["occurred_on"],
                        values["description"].strip(),
                        cents(values["amount"]),
                        values["category"],
                        values["kind"],
                        transaction_id,
                        user["id"],
                    ),
                )
            except (KeyError, ValueError):
                pass
            return redirect(start, "/transactions")

    categories = "".join(
        render_fragment(
            "partial_option.html",
            selected=" selected" if category == transaction["category"] else "",
            label=category,
        )
        for category in CATEGORIES
    )
    kinds = "".join(
        render_fragment(
            "partial_option_value.html",
            value=kind,
            selected=" selected" if kind == transaction["kind"] else "",
            label=kind.title(),
        )
        for kind in ("expense", "income")
    )
    body = render_template(
        "edit_transaction.html",
        occurred_on=transaction["occurred_on"],
        description=escape(transaction["description"]),
        amount=f"{transaction['amount_cents']/100:.2f}",
        kinds=kinds,
        categories=categories,
    )
    start("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [page("Edit transaction", body, user)]


def handle_history(env: dict, start, db, user):
    """
    Render paginated, searchable transaction history.

    :param env: The WSGI environment dictionary.
    :param start: The WSGI start_response callable.
    :param db: The database connection.
    :param user: The user information.
    :return: A WSGI response containing the transaction history page.
    """
    query = parse_qs(env.get("QUERY_STRING", ""))
    search = query.get("q", [""])[0].strip()
    try:
        page_number = int(query.get("page", ["1"])[0])
    except (TypeError, ValueError):
        page_number = 1
    page_number = max(1, page_number)
    page_size = 25

    with db() as con:
        if search:
            term = f"%{search}%"
            count = con.execute(
                """
                SELECT COUNT(*)
                FROM transactions
                WHERE user_id=?
                  AND (occurred_on LIKE ? OR description LIKE ?)
                """,
                (user["id"], term, term),
            ).fetchone()[0]
            rows = con.execute(
                """
                SELECT *
                FROM transactions
                WHERE user_id=?
                  AND (occurred_on LIKE ? OR description LIKE ?)
                ORDER BY occurred_on DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (user["id"], term, term, page_size, (page_number - 1) * page_size),
            ).fetchall()
        else:
            count = con.execute(
                "SELECT COUNT(*) FROM transactions WHERE user_id=?", (user["id"],)
            ).fetchone()[0]
            rows = con.execute(
                """
                SELECT *
                FROM transactions
                WHERE user_id=?
                ORDER BY occurred_on DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (user["id"], page_size, (page_number - 1) * page_size),
            ).fetchall()

    total_pages = max(1, (count + page_size - 1) // page_size)
    page_number = min(page_number, total_pages)
    search_param = f"&q={quote_plus(search)}" if search else ""
    body = render_template(
        "history.html",
        search_value=escape(search),
        rows=render_history_rows(rows),
        pagination=render_pagination(total_pages, page_number, search_param),
    )
    start("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [page("History", body, user)]


def handle_recurring_history(env: dict, start, db, user):
    """
    Render all automatic monthly entries for the current user.

    :param env: The WSGI environment dictionary.
    :param start: The WSGI start_response callable.
    :param db: The database connection.
    :param user: The user information.
    """
    with db() as con:
        rows = con.execute(
            """
            SELECT *
            FROM recurring_rules
            WHERE user_id=?
            ORDER BY active DESC, next_due ASC, id DESC
            """,
            (user["id"],),
        ).fetchall()

    body = render_template(
        "recurring_history.html",
        rows=render_recurring_rows(rows),
    )
    start("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [page("Automatic Monthly Entries", body, user)]


def handle_recurring_action(path: str, method: str, env: dict, start, db, user):
    """
    Edit or delete an automatic monthly entry.

    :param path: The request path.
    :param method: The HTTP method (e.g., "GET", "POST").
    :param env: The WSGI environment dictionary.
    :param start: The WSGI start_response callable.
    :param db: The database connection.
    :param user: The user information.
    :return: A WSGI response.
    """
    parts = path.strip("/").split("/")
    if len(parts) != 3 or not parts[1].isdigit() or parts[2] not in ("edit", "delete"):
        return not_found(start)

    rule_id = int(parts[1])
    with db() as con:
        rule = con.execute(
            "SELECT * FROM recurring_rules WHERE id=? AND user_id=?",
            (rule_id, user["id"]),
        ).fetchone()
        if not rule:
            return not_found(start)

        if parts[2] == "delete" and method == "POST":
            con.execute(
                "DELETE FROM recurring_rules WHERE id=? AND user_id=?",
                (rule_id, user["id"]),
            )
            return redirect(start, "/transactions/recurring")

        if parts[2] == "edit" and method == "POST":
            values = form(env)
            try:
                day = int(values["day"])
                if not 1 <= day <= 28:
                    raise ValueError("Day must be between 1 and 28")
                today = date.today()
                due = date(today.year, today.month, day)
                if due < today:
                    due = date(
                        today.year + (today.month == 12),
                        today.month % 12 + 1,
                        day,
                    )
                con.execute(
                    """
                    UPDATE recurring_rules
                    SET description=?, amount_cents=?, category=?, kind=?,
                        day_of_month=?, next_due=?, active=1
                    WHERE id=? AND user_id=?
                    """,
                    (
                        values["description"].strip(),
                        cents(values["amount"]),
                        values["category"],
                        values["kind"],
                        day,
                        due.isoformat(),
                        rule_id,
                        user["id"],
                    ),
                )
            except (KeyError, ValueError):
                pass
            return redirect(start, "/transactions/recurring")

    categories = "".join(
        render_fragment(
            "partial_option.html",
            selected=" selected" if category == rule["category"] else "",
            label=category,
        )
        for category in CATEGORIES
    )
    kinds = "".join(
        render_fragment(
            "partial_option_value.html",
            value=kind,
            selected=" selected" if kind == rule["kind"] else "",
            label=kind.title(),
        )
        for kind in ("expense", "income")
    )
    body = render_template(
        "edit_recurring.html",
        description=escape(rule["description"]),
        amount=f"{rule['amount_cents']/100:.2f}",
        kinds=kinds,
        categories=categories,
        day=rule["day_of_month"],
        delete_action=f"/recurring/{rule_id}/delete",
    )
    start("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [page("Edit Automatic Monthly Entry", body, user)]


def render_recurring_rows(rows) -> str:
    """
    Render a list of recurring rows.

    :param rows: A list of recurring rule rows from the database.
    :return: A string containing the rendered HTML for the recurring rows.
    """
    if not rows:
        return render_fragment(
            "partial_empty.html",
            columns="8",
            message="No automatic monthly entries.",
        )
    return "".join(
        render_fragment(
            "partial_recurring_row.html",
            id=row["id"],
            description=escape(row["description"]),
            amount=money(row["amount_cents"]),
            kind=row["kind"],
            kind_label=row["kind"].title(),
            category=escape(row["category"]),
            day=row["day_of_month"],
            next_due=row["next_due"],
            status="Active" if row["active"] else "Paused",
        )
        for row in rows
    )


def render_history_rows(rows) -> str:
    """
    Render a list of transaction history rows.
    :param rows: A list of transaction history rows from the database.
    :return: A string containing the rendered HTML for the transaction history rows.
    """
    if not rows:
        return render_fragment(
            "partial_empty.html", columns="7", message="No matching transactions."
        )
    return "".join(
        render_fragment(
            "partial_history_row.html",
            id=row["id"],
            occurred_on=row["occurred_on"],
            description=escape(row["description"]),
            category=escape(row["category"]),
            source=escape(row["source"].replace("_", " ").title()),
            kind=row["kind"],
            amount=money(row["amount_cents"]),
        )
        for row in rows
    )


def render_pagination(total_pages: int, current_page: int, search_param: str) -> str:
    """
    Render pagination links for transaction history.

    :param total_pages: The total number of pages available.
    :param current_page: The current page number being viewed.
    :param search_param: The search query parameter to include in pagination links.
    :return: A string containing the rendered HTML for pagination links.
    """
    if total_pages <= 1:
        return ""
    links = "".join(
        render_fragment(
            "partial_page_link.html",
            active=" active" if number == current_page else "",
            number=number,
            search_param=search_param,
        )
        for number in range(1, total_pages + 1)
    )
    return render_fragment("partial_pagination.html", links=links)
