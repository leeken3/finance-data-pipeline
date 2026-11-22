"""Authentication and session services."""

import hashlib, hmac, secrets
from datetime import datetime, timezone
from utils.formatting import cookies


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 200000
    ).hex()
    return f"{salt}${digest}"


def password_matches(password: str, stored: str) -> bool:
    return hmac.compare_digest(password_hash(password, stored.split("$", 1)[0]), stored)


def utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def session(con, user_id: int) -> str:
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
    token = cookies(env).get("expense_session")
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with db_factory() as con:
        return con.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?",
            (token_hash, utc_naive_now().isoformat()),
        ).fetchone()
