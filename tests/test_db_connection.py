import psycopg2
from etl.config import DB_CONFIG


def test_database_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("SELECT 1;")
    result = cur.fetchone()

    cur.close()
    conn.close()

    assert result[0] == 1
