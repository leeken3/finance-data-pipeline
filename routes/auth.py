"""Authentication route handlers."""

from routes.http import redirect
from services.auth import password_hash, password_matches, session
from templates.views import page, render_template
from utils.formatting import form


def handle_auth(path: str, method: str, env: dict, start, db):
    """Handle login and registration requests."""
    if method == "GET":
        action = "Log in" if path == "/login" else "Create account"
        other = "register" if path == "/login" else "login"
        link = (
            "Create an account" if other == "register" else "Already have an account?"
        )
        body = render_template("auth.html", action=action, other=other, link=link)
        start("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [page("Account", body)]

    values = form(env)
    email = values.get("email", "").strip().lower()
    password = values.get("password", "")
    with db() as con:
        existing = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if path == "/register":
            if existing or not email or len(password) < 8:
                return redirect(start, "/register")
            user_id = con.execute(
                "INSERT INTO users(email,password_hash) VALUES(?,?)",
                (email, password_hash(password)),
            ).lastrowid
        else:
            if not existing or not password_matches(
                password, existing["password_hash"]
            ):
                return redirect(start, "/login")
            user_id = existing["id"]
        token = session(con, user_id)

    start(
        "303 See Other",
        [
            ("Location", "/"),
            ("Set-Cookie", f"expense_session={token}; Path=/; HttpOnly; SameSite=Lax"),
        ],
    )
    return [b""]
