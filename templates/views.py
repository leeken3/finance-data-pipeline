"""HTML template rendering helpers."""

from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent


def render_template(name: str, **values: str) -> str:
    """
    Render a small HTML template fragment.
    :param name: The name of the template file.
    :param values: The values to replace in the template.
    :return: The rendered template.
    """
    template = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def render_fragment(name: str, **values: str) -> str:
    """
    Render a small HTML template fragment.

    :param name: The name of the template file.
    :param values: The values to replace in the template.
    :return: The rendered template.
    """
    return render_template(name, **values)


def page(title: str, body: str, user=None) -> bytes:
    """
    Render a full HTML page with a title, body, and optional navigation bar.

    :param title: The title of the page.
    :param body: The body of the page.
    :param user: The user to display in the navigation bar.
    :return: The rendered page as bytes.
    """
    nav = "" if not user else render_fragment("partial_nav.html")
    return render_template("base.html", title=title, nav=nav, body=body).encode()
