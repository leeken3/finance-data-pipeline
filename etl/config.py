import os
from dotenv import load_dotenv

load_dotenv()

"""
Configuration file for the ETL process. It loads environment variables from a .env file and provides a dictionary with the database connection parameters.
"""
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}
