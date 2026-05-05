from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
PROJECT_ROOT = SRC_DIR.parent

INPUTS_DIR = PROJECT_ROOT / "inputs"
DATA_DIR = PROJECT_ROOT / "data"
PAGES_DIR = DATA_DIR / "pages"
RAW_HTML_DIR = PAGES_DIR
DOCS_DIR = PROJECT_ROOT / "docs"
UI_DIR = PACKAGE_DIR / "ui"

PAGE_URLS_FILE = INPUTS_DIR / "page_urls.txt"
LEGACY_MONSTER_URLS_FILE = INPUTS_DIR / "monster_urls.txt"

# Compatibility aliases for existing parser internals and user-provided inputs.
MONSTER_URLS_FILE = LEGACY_MONSTER_URLS_FILE


def ensure_project_dirs() -> None:
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
