"""Dashboard and history data queries."""


def period_totals(con, user_id: int, period: str) -> dict:
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
