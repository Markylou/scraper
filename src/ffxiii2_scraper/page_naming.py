import hashlib
import re
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup


KNOWN_INDEX_TITLES = {
    "Feral_Link",
}


def page_title_from_url(url: str) -> str:
    parsed = urlparse(url)
    return unquote(parsed.path.removeprefix("/wiki/"))


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def is_index_page(title: str, html: str) -> bool:
    normalized_title = title.replace(" ", "_")
    if normalized_title in KNOWN_INDEX_TITLES:
        return True
    if normalized_title.startswith("List_of_"):
        return True

    soup = BeautifulSoup(html, "lxml")

    if soup.select_one(".disambig"):
        return False

    if soup.select_one("aside.portable-infobox, .portable-infobox"):
        return False

    for table in soup.select("table.article-table"):
        headers = [
            clean_text(cell.get_text(" ", strip=True))
            for cell in table.select("tbody tr:first-child th")
        ]
        headers = [header for header in headers if header]
        header_set = set(headers)

        if {"Monster", "Ability", "Input", "Effect", "Cooldown", "Max Synch"}.issubset(header_set):
            return True

        if headers and headers[0] == "Monster":
            return True

    return False


def safe_filename_from_title(title: str, html: str | None = None) -> str:
    prefix = ""
    if html is not None and is_index_page(title, html):
        prefix = "_INDEX_"

    base = title.replace(" ", "_")
    base = re.sub(r"[^a-zA-Z0-9._()-]+", "_", base)
    base = base[:140].strip("_")

    if prefix:
        base = base.lower()
        return f"{prefix}{base}.html"

    title_hash = hashlib.sha1(title.encode("utf-8")).hexdigest()[:10]
    return f"{base}_{title_hash}.html"
