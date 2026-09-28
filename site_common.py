"""Helpers shared by the page builders (templates, output, shared CSS)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
DEFAULT_XLSX = ROOT / "data" / "digital_devices_AI_chapter4.xlsx"
DOCS = ROOT / "docs"


def load_template(name: str) -> str:
    """Read templates/<name> and inline the shared stylesheet (%%BASE_CSS%%)."""
    html = (TEMPLATES / name).read_text(encoding="utf-8")
    return html.replace("%%BASE_CSS%%", (TEMPLATES / "base.css").read_text(encoding="utf-8"))


def fill(html: str, values: dict) -> str:
    """Replace %%KEY%% placeholders; fail loudly if any is missing or left over."""
    for key, val in values.items():
        token = f"%%{key}%%"
        if token not in html:
            raise SystemExit(f"Template is missing placeholder {token}")
        html = html.replace(token, val)
    if "%%" in html:
        left = sorted({w for w in html.split("%%")[1::2] if w.isupper()})
        if left:
            raise SystemExit(f"Unfilled placeholders: {left}")
    return html


def write_page(out: Path, html: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    (DOCS / ".nojekyll").touch()  # stop GitHub Pages running Jekyll
