import psycopg2
import pandas as pd
from etl.config import DB_CONFIG

"""
Module for analyzing transaction data and generating reports.
"""


def get_monthly_summary(year=None, month=None):
    conn = psycopg2.connect(**DB_CONFIG)

    query = """
            SELECT
                DATE_TRUNC('month', date) as month,
                category,
                COUNT(*) as transaction_count,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount
            FROM transactions
            WHERE 1=1 
            """

    params = []
    if year:
        query += " AND EXTRACT(YEAR FROM date) = %s"
        params.append(year)
    if month:
        query += " AND EXTRACT(MONTH FROM date) = %s"
        params.append(month)

    query += " GROUP BY DATE_TRUNC('month', date), category ORDER BY month DESC, total_amount DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


"""
Function to get total spending by category for a date range.
"""


def get_category_totals(start_date=None, end_date=None):
    """Get total spending by category for a date range."""
    conn = psycopg2.connect(**DB_CONFIG)

    query = """
            SELECT
                category,
                COUNT(*) as transactions,
                SUM(amount) as total,
                AVG(amount) as average,
                MIN(amount) as min_amount,
                MAX(amount) as max_amount
            FROM transactions
            WHERE 1=1 
            """

    params = []
    if start_date:
        query += " AND date >= %s"
        params.append(start_date)
    if end_date:
        query += " AND date <= %s"
        params.append(end_date)

    query += " GROUP BY category ORDER BY total DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


"""
Function to get total spending per month.
"""


def get_monthly_totals():
    """Get total spending per month."""
    conn = psycopg2.connect(**DB_CONFIG)

    query = """
            SELECT
                DATE_TRUNC('month', date) as month,
            COUNT(*) as transactions,
            SUM(amount) as total_spent
            FROM transactions
            GROUP BY DATE_TRUNC('month', date)
            ORDER BY month DESC \
            """

    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


"""
Function to generate a comprehensive expense report.
"""


def generate_expense_report(year=None, month=None):
    """Generate a comprehensive expense report."""
    print("=" * 60)
    print("EXPENSE REPORT")
    print("=" * 60)

    # Monthly summary
    print("\nMONTHLY SUMMARY BY CATEGORY:")
    summary = get_monthly_summary(year, month)
    print(summary.to_string(index=False))

    # Category totals
    print("\n\nCATEGORY BREAKDOWN:")
    categories = get_category_totals()
    print(categories.to_string(index=False))

    # Monthly totals
    print("\n\nMONTHLY TOTALS:")
    monthly = get_monthly_totals()
    print(monthly.to_string(index=False))

    print("\n" + "=" * 60)


"""
Main function to run the report.
"""
if __name__ == "__main__":
    generate_expense_report()
