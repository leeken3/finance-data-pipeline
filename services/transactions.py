"""Transaction and recurring-entry business logic."""

from datetime import date


def is_expense_transaction(transaction_type: str, description: str, amount) -> bool:
    """
    Distinguish purchases from payments and credits in bank exports.

    :param transaction_type: The type of the transaction (e.g., debit, credit).
    :param description: The description of the transaction.
    :param amount: The amount of the transaction.
    :return: True if the transaction is an expense, False otherwise.
    """
    kind = (transaction_type or "").strip().lower()
    merchant = (description or "").strip().lower()
    if kind:
        if "debit" in kind or "purchase" in kind:
            return True
        if "credit" in kind or "payment" in kind or "refund" in kind:
            return False
    if (
        merchant.startswith("payment")
        or "payment received" in merchant
        or "thank you" in merchant
    ):
        return False
    return amount > 0


def delete_transaction_ids(con, user_id: int, ids) -> int:
    """
    Delete transactions by their IDs.

    :param con: The database connection object.
    :param user_id: The ID of the user for whom to delete transactions.
    :param ids: A list of transaction IDs to delete.
    :return: The number of rows deleted.
    """
    valid_ids = [int(value) for value in ids if str(value).isdigit()]
    if not valid_ids:
        return 0
    placeholders = ",".join("?" for _ in valid_ids)
    result = con.execute(
        f"DELETE FROM transactions WHERE user_id=? AND id IN ({placeholders})",
        (user_id, *valid_ids),
    )
    return result.rowcount


def apply_recurring(con, user_id: int) -> None:
    """
    Apply recurring rules to generate transactions for a user.

    :param con: The database connection object.
    :param user_id: The ID of the user for whom to apply recurring rules.
    :return: None
    """
    today = date.today()
    for rule in con.execute(
        """
        SELECT *
        FROM recurring_rules
        WHERE user_id=?
          AND active=1
          AND next_due<=?
        """,
        (user_id, today.isoformat()),
    ).fetchall():
        due = date.fromisoformat(rule["next_due"])
        while due <= today:
            con.execute(
                """
                INSERT OR IGNORE INTO transactions (
                    user_id, occurred_on, description, amount_cents,
                    category, kind, source, import_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    due.isoformat(),
                    rule["description"],
                    rule["amount_cents"],
                    rule["category"],
                    rule["kind"],
                    "recurring",
                    f"rule:{rule['id']}:{due}",
                ),
            )
            due = date(
                due.year + (due.month == 12), due.month % 12 + 1, rule["day_of_month"]
            )
        con.execute(
            "UPDATE recurring_rules SET next_due=? WHERE id=?",
            (due.isoformat(), rule["id"]),
        )


def yearly_totals(con, user_id: int, year: str) -> tuple[int, int]:
    """
    Get the total income and expense amounts for a user in a given year.

    :param con: The database connection object.
    :param user_id: The ID of the user for whom to get yearly totals.
    :param year: The year for which to get totals.
    :return: A tuple of (income, expense) amounts.
    """
    totals = {
        row["kind"]: row["total"]
        for row in con.execute(
            """
            SELECT kind, COALESCE(SUM(amount_cents), 0) AS total
            FROM transactions
            WHERE user_id=? AND substr(occurred_on,1,4)=?
            GROUP BY kind
            """,
            (user_id, year),
        )
    }
    return totals.get("income", 0), totals.get("expense", 0)
