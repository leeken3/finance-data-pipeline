"""Authentication and session services."""

import hashlib, hmac, secrets
from datetime import datetime, timezone
from utils.formatting import cookies


def password_hash(password: str, salt: str | None = None) -> str:
    """
    Function to hash a password with an optional salt using PBKDF2-HMAC-SHA256.

    :param password: The password to hash.
    :param salt: The salt to use for hashing, or None to generate a new one.
    :return: The hashed password with the salt prepended.
    """
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 200000
    ).hex()
    return f"{salt}${digest}"


def password_matches(password: str, stored: str) -> bool:
    """
    Check if a password matches a stored hash.

    :param password: The password to check.
    :param stored: The stored password hash.
    :return: True if the password matches, False otherwise.
    """
    return hmac.compare_digest(password_hash(password, stored.split("$", 1)[0]), stored)


def utc_naive_now() -> datetime:
    """
    Get the current UTC time as a naive datetime object (without timezone info).

    :return: The current UTC time as a naive datetime object.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def session(con, user_id: int) -> str:
    """
    Create a new session for a user and return the session token.

    :param con: The database connection object.
    :param user_id: The ID of the user for whom to create the session.
    :return: The session token as a string.
    """
    token = secrets.token_urlsafe(32)
    con.execute(
        "DELETE FROM sessions WHERE expires_at<?", (utc_naive_now().isoformat(),)
    )
    con.execute(
        "INSERT INTO sessions VALUES(?,?,?)",
        (hashlib.sha256(token.encode()).hexdigest(), user_id, "2099-01-01T00:00:00"),
    )
    return token


def current_user(env: dict, db_factory):
    """
    Retrieve the current user based on the session token in the request cookies.

    :param env: The WSGI environment dictionary containing request information.
    :param db_factory: A callable that returns a database connection context manager.
    :return: The user record from the database if a valid session exists, or None otherwise.
    """
    token = cookies(env).get("expense_session")
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with db_factory() as con:
        return con.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?",
            (token_hash, utc_naive_now().isoformat()),
        ).fetchone()
