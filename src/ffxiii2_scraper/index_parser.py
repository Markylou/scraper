from urllib.parse import urljoin
from urllib.parse import quote

from bs4 import BeautifulSoup

from .paths import MONSTER_URLS_FILE, PARADIGM_PACK_INDEX_FILE, ensure_project_dirs


BASE_WIKI_URL = "https://finalfantasy.fandom.com"


def parse_monster_links(index_html: str) -> list[str]:
    soup = BeautifulSoup(index_html, "lxml")
    monster_urls: list[str] = []
    seen: set[str] = set()

    for table in soup.select("table.article-table"):
        header_cells = [
            cell.get_text(" ", strip=True)
            for cell in table.select("tbody tr:first-child th")
        ]
        if not header_cells or header_cells[0] != "Monster":
            continue

        for row in table.select("tbody tr")[1:]:
            monster_cell = row.select_one("th")
            if monster_cell is None:
                continue

            link = monster_cell.select_one('a[href^="/wiki/"]')
            if link is None:
                continue

            href = link.get("href")
            if not href:
                continue

            link_classes = set(link.get("class", []))
            if "mw-disambig" in link_classes:
                display_name = link.get_text(" ", strip=True)
                if display_name:
                    href = f"/wiki/{quote(display_name.replace(' ', '_') + '_(Final_Fantasy_XIII-2)')}"

            absolute_url = urljoin(BASE_WIKI_URL, href)
            if absolute_url in seen:
                continue

            seen.add(absolute_url)
            monster_urls.append(absolute_url)

    return monster_urls


def main() -> None:
    ensure_project_dirs()
    if not PARADIGM_PACK_INDEX_FILE.exists():
        raise FileNotFoundError(f"Could not find {PARADIGM_PACK_INDEX_FILE}")

    monster_urls = parse_monster_links(
        PARADIGM_PACK_INDEX_FILE.read_text(encoding="utf-8")
    )

    MONSTER_URLS_FILE.write_text(
        "\n".join(monster_urls) + ("\n" if monster_urls else ""),
        encoding="utf-8",
    )

    print(f"Extracted {len(monster_urls)} monster URLs")
    print(f"Saved: {MONSTER_URLS_FILE}")
