"""Environment and application settings."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "expense_tracker.db"
CATEGORIES = [
    "Restaurants",
    "Groceries",
    "Fitness & gym",
    "Clothing",
    "Entertainment",
    "Transport",
    "Bills",
    "Housing",
    "Health",
    "Shopping",
    "Travel",
    "Cash & transfers",
    "Income",
    "Other",
]
OLLAMA_URL = os.getenv("LEDGER_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("LEDGER_OLLAMA_MODEL", "llama3.2:1b")
