"""Formatting and HTTP form utilities."""

from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs


def money(cents: int) -> str:
    return f"{'-' if cents < 0 else ''}${abs(cents)/100:,.2f}"


def cents(value: str) -> int:
    cleaned = (
        value.replace("$", "")
        .replace(",", "")
        .strip()
        .replace("(", "-")
        .replace(")", "")
    )
    try:
        return int(Decimal(cleaned).copy_abs() * 100)
    except InvalidOperation as exc:
        raise ValueError("Invalid currency amount") from exc


def cookies(env: dict) -> dict:
    return dict(
        item.strip().split("=", 1)
        for item in env.get("HTTP_COOKIE", "").split(";")
        if "=" in item
    )


def form(env: dict) -> dict:
    raw = env["wsgi.input"].read(int(env.get("CONTENT_LENGTH") or 0)).decode()
    return {key: values[0] for key, values in parse_qs(raw).items()}


def form_values(env: dict) -> dict:
    raw = env["wsgi.input"].read(int(env.get("CONTENT_LENGTH") or 0)).decode()
    return parse_qs(raw)
