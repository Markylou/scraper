from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
PROJECT_ROOT = SRC_DIR.parent

INPUTS_DIR = PROJECT_ROOT / "inputs"
DATA_DIR = PROJECT_ROOT / "data"
RAW_HTML_DIR = DATA_DIR / "raw_html"
PARSED_DIR = DATA_DIR / "parsed"
PARSED_MONSTERS_DIR = PARSED_DIR / "monsters"
PARSED_FERAL_LINKS_DIR = PARSED_DIR / "feral_links"
SCHEMAS_DIR = DATA_DIR / "schemas"
DOCS_DIR = PROJECT_ROOT / "docs"

MONSTER_URLS_FILE = INPUTS_DIR / "monster_urls.txt"
PARADIGM_PACK_INDEX_FILE = RAW_HTML_DIR / "_INDEX_paradigm_pack_monsters.html"
FERAL_LINK_INDEX_FILE = RAW_HTML_DIR / "_INDEX_feral_link.html"
MONSTER_RAW_SCHEMA_FILE = SCHEMAS_DIR / "monster.raw.schema.json"
FERAL_LINK_RAW_SCHEMA_FILE = SCHEMAS_DIR / "feral_link.raw.schema.json"


def ensure_project_dirs() -> None:
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_MONSTERS_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_FERAL_LINKS_DIR.mkdir(parents=True, exist_ok=True)
