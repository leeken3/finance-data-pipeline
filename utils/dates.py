"""Date parsing and selected-period helpers."""

from datetime import date, datetime, timedelta


def parse_statement_date(value: str) -> str:
    """Accept common bank export date formats and return ISO YYYY-MM-DD."""
    cleaned = str(value).strip().strip("\"'")
    patterns = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%d-%b-%y",
        "%d-%b-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%m-%d-%Y",
        "%m-%d-%y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %d %Y",
        "%B %d %Y",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    )
    for pattern in patterns:
        try:
            return datetime.strptime(cleaned, pattern).date().isoformat()
        except ValueError:
            continue

    # Support numeric Excel serial dates exported by some bank spreadsheets.
    try:
        serial = float(cleaned)
        if serial > 20000:
            return (date(1899, 12, 30) + timedelta(days=serial)).isoformat()
    except (TypeError, ValueError, OverflowError):
        pass

    raise ValueError(f"Unsupported statement date: {value}")


def selected_period(value):
    try:
        return datetime.strptime(value, "%Y-%m").strftime("%Y-%m")
    except (TypeError, ValueError):
        return date.today().strftime("%Y-%m")
