"""Dashboard route and rendering."""

from datetime import date, datetime
from html import escape
from urllib.parse import parse_qs

from config.settings import CATEGORIES
from services.dashboard import (
    category_totals,
    expense_series,
    period_totals,
    recent_transactions,
)
from services.transactions import apply_recurring, yearly_totals
from templates.views import page, render_fragment, render_template
from utils.dates import selected_period
from utils.formatting import money, cookies


def period_calendar(selected: str) -> str:
    year = int(selected[:4])
    month = int(selected[5:7])
    months = "".join(
        render_fragment(
            "partial_month_choice.html",
            value=f"{number:02d}",
            current=" current" if number == month else "",
            label=date(2000, number, 1).strftime("%b"),
        )
        for number in range(1, 13)
    )
    return render_template(
        "period_calendar.html",
        selected_label=datetime.strptime(selected, "%Y-%m").strftime("%B %Y"),
        year=year,
        year_limit=date.today().year + 25,
        months=months,
    )


def handle_dashboard(env: dict, start, db, user, notice=None):
    """Build dashboard context and render the dashboard template."""
    query = parse_qs(env.get("QUERY_STRING", ""))
    month = query.get("month", [None])[0]
    year = query.get("year", [None])[0]
    if month and "-" not in month:
        month = f"{year or date.today().year}-{month.zfill(2)}"
    if not month:
        month = cookies(env).get("dashboard_period")
    period = selected_period(month)

    with db() as con:
        apply_recurring(con, user["id"])
        totals = period_totals(con, user["id"], period)
        categories = category_totals(con, user["id"], period)
        recent = recent_transactions(con, user["id"], period)
        series = expense_series(con, user["id"], period)
        yearly_income, yearly_expense = yearly_totals(con, user["id"], period[:4])

    net_value = totals.get("income", 0) - totals.get("expense", 0)
    yearly_net = yearly_income - yearly_expense
    context = {
        "today": date.today().isoformat(),
        "period_name": datetime.strptime(period, "%Y-%m").strftime("%B %Y"),
        "period_picker": period_calendar(period),
        "notice": (
            render_fragment("partial_flash.html", message=escape(notice))
            if notice
            else ""
        ),
        "monthly_income": money(totals.get("income", 0)),
        "monthly_expense": money(totals.get("expense", 0)),
        "net_value": money(net_value),
        "net_class": "positive" if net_value >= 0 else "negative",
        "year": period[:4],
        "yearly_income": money(yearly_income),
        "yearly_expense": money(yearly_expense),
        "yearly_net": money(yearly_net),
        "yearly_net_class": "positive" if yearly_net >= 0 else "negative",
        "category_options": "".join(
            render_fragment("partial_option.html", selected="", label=category)
            for category in CATEGORIES
        ),
        "bars": render_category_bars(categories),
        "columns": render_expense_columns(series),
        "category_rows": render_category_rows(categories),
        "recent_rows": render_recent_rows(recent),
    }
    body = render_template("dashboard.html", **context)
    start(
        "200 OK",
        [
            ("Content-Type", "text/html; charset=utf-8"),
            (
                "Set-Cookie",
                f"dashboard_period={period}; Max-Age=31536000; Path=/; HttpOnly; SameSite=Lax",
            ),
        ],
    )
    return [page("Dashboard", body, user)]


def render_category_bars(categories) -> str:
    if not categories:
        return render_fragment(
            "partial_message.html", message="No expenses for this month."
        )
    max_category = max(row["total"] for row in categories)
    palette = ["coral", "violet", "blue", "gold", "mint"]
    return "".join(
        render_fragment(
            "partial_category_bar.html",
            category=escape(row["category"]),
            palette=palette[index % len(palette)],
            width=max(8, round(row["total"] / max_category * 100)),
            amount=money(row["total"]),
        )
        for index, row in enumerate(categories[:5])
    )


def render_expense_columns(series) -> str:
    if not series:
        return render_fragment("partial_message.html", message="No history yet.")
    max_series = max(row["total"] for row in series)
    return "".join(
        render_fragment(
            "partial_month_column.html",
            amount=money(row["total"]),
            height=max(10, round(row["total"] / max_series * 130)),
            month=datetime.strptime(row["month"], "%Y-%m").strftime("%b"),
        )
        for row in reversed(series)
    )


def render_category_rows(categories) -> str:
    if not categories:
        return render_fragment(
            "partial_empty.html", columns="2", message="No expenses this month."
        )
    return "".join(
        render_fragment(
            "partial_category_row.html",
            category=escape(row["category"]),
            amount=money(row["total"]),
        )
        for row in categories
    )


def render_recent_rows(recent) -> str:
    if not recent:
        return render_fragment(
            "partial_empty.html", columns="4", message="No entries yet."
        )
    return "".join(
        render_fragment(
            "partial_recent_row.html",
            occurred_on=row["occurred_on"],
            description=escape(row["description"]),
            category=escape(row["category"]),
            kind=row["kind"],
            amount=money(row["amount_cents"]),
        )
        for row in recent
    )
