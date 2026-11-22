# Ledger

Local minimal expense tracking for credit-card CSV imports, manual cash entries, scheduled monthly entries, and user-specific history.

## Start

```powershell
.\.venv\Scripts\python.exe app.py
```

Open `http://127.0.0.1:8000`, create an account, and add/import transactions. Data is stored locally in `data/expense_tracker.db`.

You can also run:

```powershell
.\expenses run
```

`expenses run` opens `http://127.0.0.1:8000/` in Google Chrome when installed (otherwise it falls back to your default browser).

If you want to run `expenses run` without `.\`, add this project directory to your user `PATH`.

## Project structure

- `app.py` — WSGI entry point and route registration
- `config/` — environment settings and editable `merchant_rules.py` categorization data
- `database.py` — SQLite connection and schema initialization
- `routes/` — focused HTTP handlers for auth, dashboard, imports, history, static assets
- `services/` — authentication, categorization, transaction, import, and dashboard logic
- `utils/` — reusable formatting and date helpers
- `templates/` — base, auth, dashboard, history, calendar, and edit HTML templates
- `static/css/` — reusable base, dashboard, and history styles
- `static/js/` — shared, dashboard, calendar, and history browser interactions
- HTML fragments are rendered from `templates/partial_*.html` files rather than route/Python markup
- `tests/` — application test suite

## History views

History includes a tab for viewing every automatic monthly entry. From that view, entries can be opened, edited, or deleted. Editing recalculates the next due date and reactivates the entry.

## CSV imports

Bank exports may use comma, semicolon, or tab separators and common date formats such as `21-Nov-26`, `YYYY-MM-DD`, or `MM/DD/YYYY`. The importer also extracts CSV files from standard multipart uploads and supports amount formats with commas, currency symbols, trailing minus signs, and parentheses.

Upload a CSV containing `date`, `description`, and `amount` columns (common aliases are accepted). Dates must use `YYYY-MM-DD`; duplicate statement rows are skipped.

## Free local AI categorization

Imports are categorized by the locally installed free Ollama model (`llama3.2:1b`). It receives only merchant descriptions, runs entirely on this computer, and returns categories such as Restaurants, Groceries, Fitness & gym, Clothing, and Entertainment. If Ollama is unavailable, Ledger uses local merchant rules instead, so imports never fail.

Start Ollama before importing if it is not already running:

```powershell
ollama serve
```
