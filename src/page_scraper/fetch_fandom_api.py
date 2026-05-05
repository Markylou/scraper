import time
from urllib.parse import unquote
from uuid import uuid4

import requests
from bs4 import BeautifulSoup

from .core.job_output import job_output_root
from .io_utils import load_urls
from .page_archive import archive_page
from .page_naming import page_title_from_url
from .paths import PAGE_URLS_FILE, ensure_project_dirs


REQUEST_DELAY_SECONDS = 1
API_URL = "https://finalfantasy.fandom.com/api.php"
USER_AGENT = "FFXIII2WikiScraper/0.1 (personal learning project)"

def fetch_parsed_html(title: str) -> str:
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
        "formatversion": "2",
    }

    response = requests.get(
        API_URL,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    if "error" in data:
        raise RuntimeError(data["error"])

    return data["parse"]["text"]


def resolve_disambiguation_title(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    disambig = soup.select_one(".disambig")
    if disambig is None:
        return None

    for link in soup.select('ul li a[href^="/wiki/"]'):
        href = link.get("href") or ""
        title = link.get("title") or ""
        text = link.get_text(" ", strip=True)
        if "Final Fantasy XIII-2" in title or "Final Fantasy XIII-2" in text or "Final_Fantasy_XIII-2" in href:
            return unquote(href.removeprefix("/wiki/"))

    return None


def fetch_fandom_url(url: str) -> tuple[str, str]:
    title = page_title_from_url(url)
    html = fetch_parsed_html(title)
    resolved_title = resolve_disambiguation_title(html)
    if resolved_title and resolved_title != title:
        title = resolved_title
        html = fetch_parsed_html(title)
    return title, html


def main() -> None:
    ensure_project_dirs()
    urls = load_urls(PAGE_URLS_FILE)

    print(f"Loaded {len(urls)} URLs")
    if not urls:
        print("Done.")
        return

    pages_dir = job_output_root(urls[0], uuid4().hex) / "pages"

    for i, url in enumerate(urls, start=1):
        try:
            title = page_title_from_url(url)
            print(f"[{i}/{len(urls)}] Fetching API HTML: {title}")

            title, html = fetch_fandom_url(url)

            archive = archive_page(url=url, final_url=url, title=title, html=html, strategy="fandom", pages_dir=pages_dir)

            print(f"  Saved: {archive.folder.name}")
            time.sleep(REQUEST_DELAY_SECONDS)
        except Exception as exc:
            print(f"  Failed: {url}")
            print(f"  Error: {exc}")

    print("Done.")
