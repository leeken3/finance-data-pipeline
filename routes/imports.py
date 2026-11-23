"""CSV import route handler."""

import csv
import hashlib
import io
from decimal import Decimal, InvalidOperation
import re
from urllib.parse import quote_plus

from routes.http import redirect
from services.transactions import is_expense_transaction
from utils.dates import parse_statement_date


def extract_csv_payload(raw: bytes, content_type: str = "") -> str:
    """
    Extract the uploaded CSV from multipart/form-data or return plain CSV text.

    :param raw: The raw bytes of the HTTP request body.
    :param content_type: The Content-Type header of the HTTP request.
    :return: The extracted CSV payload as a string.
    """
    boundary = ""
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("boundary="):
            boundary = part.split("=", 1)[1].strip('"')

    if boundary:
        for chunk in raw.split(f"--{boundary}".encode("ascii")):
            if b'name="statement"' not in chunk and b"filename=" not in chunk:
                continue
            header, separator, body = chunk.partition(b"\r\n\r\n")
            if not separator:
                header, separator, body = chunk.partition(b"\n\n")
            if separator:
                body = body.rstrip(b"\r\n-")
                return body.decode("utf-8-sig", errors="replace")

    text = raw.decode("utf-8-sig", errors="replace")
    for separator in ("\r\n\r\n", "\n\n"):
        if separator in text:
            text = text.split(separator, 1)[-1]
    if "\r\n--" in text:
        text = text.rsplit("\r\n--", 1)[0]
    elif "\n--" in text:
        text = text.rsplit("\n--", 1)[0]
    return text.strip()


def normalized_header(value: str) -> str:
    """
    Normalize a CSV header by lowercasing and removing non-alphanumeric characters.

    :param value: The header string to normalize.
    :return: The normalized header string.
    """
    return re.sub(r"[^a-z0-9]", "", value.lower())


def parse_amount(value: str) -> Decimal:
    """
    Parse common currency formats, including $1,234.50 and (12.25).

    :param value: The string to parse.
    :return: The parsed Decimal value.
    """
    text = (
        str(value)
        .strip()
        .replace("\u00a0", " ")
        .replace("$", "")
        .replace("€", "")
        .replace("£", "")
    )
    text = text.replace(",", "").replace("'", "").strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    if text.endswith("-"):
        negative = True
        text = text[:-1]
    text = text.replace("+", "").strip()
    amount = Decimal(text)
    return -amount if negative else amount


def find_column(headers: dict, aliases: tuple) -> str:
    """
    Find the original header name for a normalized header from a list of aliases.

    :param headers: A dictionary mapping normalized header names to original header names.
    :param aliases: A tuple of possible normalized header names.
    :return: The original header name.
    """
    for normalized, original in headers.items():
        if normalized in aliases:
            return original
    raise KeyError("Required CSV column not found")


def handle_import(env: dict, start, db, user, categorize_descriptions):
    """
    Parse a bank statement, classify purchases, and insert unique expenses.
    Embedded try/except blocks are used to handle errors in individual rows without stopping the entire import process.

    :param env: The WSGI environment.
    :param start: The WSGI start function.
    :param db: The database connection.
    :param user: The user information.
    :param categorize_descriptions: A function to categorize transaction descriptions.
    :return: A redirect response to the start page with a notice message.
    """
    raw = env["wsgi.input"].read(int(env.get("CONTENT_LENGTH") or 0))
    payload = extract_csv_payload(raw, env.get("CONTENT_TYPE", ""))
    try:
        try:
            dialect = csv.Sniffer().sniff(payload[:4096], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(io.StringIO(payload), dialect=dialect)
        headers = {
            normalized_header(header): header
            for header in (reader.fieldnames or [])
            if header
        }
        date_key = find_column(
            headers,
            ("date", "transactiondate", "posteddate", "postingdate", "trxndate"),
        )
        description_key = find_column(
            headers,
            (
                "description",
                "transactiondescription",
                "merchant",
                "merchantname",
                "name",
                "details",
                "memo",
                "narration",
            ),
        )
        try:
            amount_key = find_column(
                headers,
                (
                    "amount",
                    "transactionamount",
                    "total",
                    "value",
                    "debit",
                    "withdrawal",
                    "purchaseamount",
                ),
            )
        except KeyError:
            amount_key = None
        debit_key = next(
            (
                original
                for normalized, original in headers.items()
                if normalized in ("debit", "withdrawal", "purchaseamount")
            ),
            None,
        )
        credit_key = next(
            (
                original
                for normalized, original in headers.items()
                if normalized in ("credit", "deposit", "payment")
            ),
            None,
        )
        type_key = next(
            (
                original
                for normalized, original in headers.items()
                if normalized
                in (
                    "transaction",
                    "type",
                    "transactiontype",
                    "debitcredit",
                )
            ),
            None,
        )
        statement_rows = [
            row
            for row in reader
            if row.get(description_key, "").strip()
            and (
                (amount_key and row.get(amount_key, "").strip())
                or (debit_key and row.get(debit_key, "").strip())
                or (credit_key and row.get(credit_key, "").strip())
            )
        ]

        imported = skipped = credits = 0
        expense_rows = []
        for row in statement_rows:
            try:
                if amount_key:
                    value = parse_amount(row[amount_key])
                elif debit_key and row.get(debit_key, "").strip():
                    value = parse_amount(row[debit_key])
                    value = abs(value)
                elif credit_key:
                    value = parse_amount(row[credit_key])
                    if value:
                        credits += 1
                        continue
                else:
                    raise KeyError("No amount column found")
                if not is_expense_transaction(
                    row.get(type_key, "") if type_key else "",
                    row[description_key],
                    value,
                ):
                    credits += 1
                    continue
                expense_rows.append((row, value))
            except (InvalidOperation, KeyError):
                skipped += 1

        categories = categorize_descriptions(
            [row[description_key].strip() for row, value in expense_rows], user["id"]
        )
        with db() as con:
            for (row, value), category in zip(expense_rows, categories):
                try:
                    description = row[description_key].strip()
                    occurred = parse_statement_date(row[date_key])
                    key = hashlib.sha256(
                        f"{occurred}|{description}|{value}".encode()
                    ).hexdigest()
                    result = con.execute(
                        """
                        INSERT OR IGNORE INTO transactions (
                            user_id, occurred_on, description, amount_cents,
                            category, kind, source, import_key
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user["id"],
                            occurred,
                            description,
                            int(abs(value) * 100),
                            category,
                            "expense",
                            "card import",
                            key,
                        ),
                    )
                    imported += max(result.rowcount, 0)
                except (ValueError, InvalidOperation, KeyError):
                    skipped += 1
        message = (
            f"Imported {imported} transaction(s)."
            + (f" Skipped {credits} card payment/refund row(s)." if credits else "")
            + (f" Skipped {skipped} invalid row(s)." if skipped else "")
        )
    except (StopIteration, ValueError, KeyError):
        message = (
            "Could not read that CSV. It needs Date, Description, and Amount columns."
        )
    return redirect(start, "/?notice=" + quote_plus(message))
