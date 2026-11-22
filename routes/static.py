"""Static asset delivery."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def handle_static(path: str, start):
    """Serve an allow-listed static CSS or JavaScript file."""
    relative = path.removeprefix("/static/")
    file_path = ROOT / "static" / Path(*relative.split("/"))
    if not file_path.is_file() or file_path.suffix.lower() not in (".css", ".js"):
        start("404 Not Found", [("Content-Type", "text/plain")])
        return [b"Not found"]
    content_type = (
        "text/css" if file_path.suffix.lower() == ".css" else "application/javascript"
    )
    start("200 OK", [("Content-Type", content_type)])
    return [file_path.read_bytes()]
