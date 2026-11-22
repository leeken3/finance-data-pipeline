"""Shared WSGI response helpers."""


def redirect(start, location: str):
    """Send a 303 redirect response."""
    start("303 See Other", [("Location", location)])
    return [b""]


def html_response(start, body: bytes, status="200 OK"):
    start(status, [("Content-Type", "text/html; charset=utf-8")])
    return [body]


def not_found(start):
    start("404 Not Found", [("Content-Type", "text/plain")])
    return [b"Not found"]
