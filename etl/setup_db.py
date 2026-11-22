import psycopg2
from pathlib import Path
from etl.config import DB_CONFIG

"""
Script to set up database tables for the ETL process.
"""


def setup_database():
    """Create database tables if they don't exist."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Read and execute schema file
