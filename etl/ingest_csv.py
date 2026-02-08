import pandas as pd
import psycopg2
from pathlib import Path
from etl.config import DB_CONFIG


def read_csv(file_path):
    """Read and validate CSV file."""
    df = pd.read_csv(file_path)

    # Add validation for required columns
    required_columns = ['date', 'description', 'amount', 'category']
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return df