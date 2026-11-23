"""Dashboard and history data queries."""


def period_totals(con, user_id: int, period: str) -> dict:
    """
    Get the total amounts for each transaction kind (expense, income, transfer) for a user in a given period.

    :param con: The database connection object.
    :param user_id: The ID of the user for whom to get period totals.
    :param period: The period for which to get totals.
    :return: A dictionary mapping transaction kinds to their total amounts.
    """
    return {
        row["kind"]: row["total"]
        for row in con.execute(
            """
            SELECT kind, COALESCE(SUM(amount_cents), 0) AS total
            FROM transactions
            WHERE user_id=? AND substr(occurred_on,1,7)=?
            GROUP BY kind
            """,
            (user_id, period),
        )
    }


def category_totals(con, user_id: int, period: str):
    """
    Get the total amounts for each category of expense transactions for a user in a given period.

    :param con: The database connection object.
    :param user_id: The ID of the user for whom to get category totals.
    :param period: The period for which to get totals.
    :return: A list of dictionaries, each containing a category and its total amount.
    """
    return con.execute(
        """
        SELECT category, SUM(amount_cents) AS total
        FROM transactions
        WHERE user_id=?
          AND kind='expense'
          AND substr(occurred_on,1,7)=?
        GROUP BY category
        ORDER BY total DESC
        """,
        (user_id, period),
    ).fetchall()


def recent_transactions(con, user_id: int, period: str):
    """
    Get the most recent transactions for a user in a given period.

    :param con: The database connection object.
    :param user_id: The ID of the user for whom to get recent transactions.
    :param period: The period for which to get recent transactions.
    :return: A list of dictionaries, each containing a transaction.
    """
    return con.execute(
        """
        SELECT *
        FROM transactions
        WHERE user_id=? AND substr(occurred_on,1,7)=?
        ORDER BY occurred_on DESC, id DESC
        LIMIT 8
        """,
        (user_id, period),
    ).fetchall()


def expense_series(con, user_id: int, period: str):
    """
    Get the total expense amounts for each month up to a given period for a user.

    :param con: The database connection object.
    :param user_id: The ID of the user for whom to get expense series.
    :param period: The period up to which to get expense series.
    :return: A list of dictionaries, each containing a month and its total expense amount.
    """
    return con.execute(
        """
        SELECT substr(occurred_on,1,7) AS month,
               SUM(amount_cents) AS total
        FROM transactions
        WHERE user_id=?
          AND kind='expense'
          AND occurred_on<=?
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
        """,
        (user_id, f"{period}-31"),
    ).fetchall()
