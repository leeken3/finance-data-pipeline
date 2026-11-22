"""HTML template rendering helpers."""

from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent


def render_template(name: str, **values: str) -> str:
    template = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def render_fragment(name: str, **values: str) -> str:
    """Render a small HTML template fragment."""
    return render_template(name, **values)


def page(title: str, body: str, user=None) -> bytes:
    nav = "" if not user else render_fragment("partial_nav.html")
    return render_template("base.html", title=title, nav=nav, body=body).encode()
