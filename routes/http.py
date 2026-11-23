"""Shared WSGI response helpers."""


def redirect(start, location: str):
    """
    Send a 303 redirect response.

    :param start: The WSGI start_response callable.
    :param location: The URL to redirect to.
    :return: A list containing an empty response body.
    """
    start("303 See Other", [("Location", location)])
    return [b""]


def html_response(start, body: bytes, status="200 OK"):
    """
    Send an HTML response.

    :param start: The WSGI start_response callable.
    :param body: The HTML body as bytes.
    :param status: The HTTP status code.
    :return: A list containing the response body as bytes.
    """
    start(status, [("Content-Type", "text/html; charset=utf-8")])
    return [body]


def not_found(start):
    """
    Function to send a 404 Not Found response.

    :param start:
    :return:
    """
    start("404 Not Found", [("Content-Type", "text/plain")])
    return [b"Not found"]
