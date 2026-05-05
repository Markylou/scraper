import asyncio
from collections.abc import Callable
from dataclasses import asdict, dataclass

from .fetch_fandom_api import fetch_fandom_url
from .fetch_playwright import fetch_page_html
from .fetch_requests import fetch_url, html_needs_browser
from .page_archive import archive_page
from .page_naming import page_title_from_url
from .paths import PAGES_DIR, ensure_project_dirs
from .url_utils import classify_url


ProgressCallback = Callable[[str], None]


@dataclass(frozen=True)
class ScrapeOutcome:
    url: str
    strategy: str
    saved_folder: str | None
    ok: bool
    message: str
    files: dict[str, str] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def choose_strategy(url: str) -> str:
    if classify_url(url) == "fandom":
        return "fandom"
    return "requests"


def scrape_urls(urls: list[str], progress: ProgressCallback | None = None) -> list[ScrapeOutcome]:
    ensure_project_dirs()
    outcomes: list[ScrapeOutcome] = []

    for index, url in enumerate(urls, start=1):
        if progress:
            progress(f"Saving page {index} of {len(urls)}")
        try:
            outcome = scrape_one_url(url)
        except Exception as exc:
            outcome = ScrapeOutcome(url=url, strategy="unknown", saved_folder=None, ok=False, message=str(exc))
        outcomes.append(outcome)

    return outcomes


def scrape_one_url(url: str) -> ScrapeOutcome:
    strategy = choose_strategy(url)
    if strategy == "fandom":
        title, html = fetch_fandom_url(url)
        archive = archive_page(url=url, final_url=url, title=title, html=html, strategy="fandom")
        return ScrapeOutcome(
            url=url,
            strategy="fandom",
            saved_folder=archive_path(archive.folder),
            ok=True,
            message="Saved with wiki shortcut",
            files=archive_files(archive.folder),
        )

    result = fetch_url(url)
    html = result.html
    final_url = result.final_url
    used_strategy = "requests"

    if html_needs_browser(html):
        final_url, html = asyncio.run(fetch_page_html(url))
        used_strategy = "browser"

    title = page_title_from_url(final_url)
    archive = archive_page(url=url, final_url=final_url, title=title, html=html, strategy=used_strategy)
    return ScrapeOutcome(
        url=url,
        strategy=used_strategy,
        saved_folder=archive_path(archive.folder),
        ok=True,
        message="Saved",
        files=archive_files(archive.folder),
    )


def archive_path(folder) -> str:
    return folder.relative_to(PAGES_DIR).as_posix()


def archive_files(folder) -> dict[str, str]:
    base = f"data/pages/{archive_path(folder)}"
    return {
        "source_html": f"{base}/source.html",
        "content_html": f"{base}/content.html",
        "markdown": f"{base}/content.md",
        "metadata": f"{base}/metadata.json",
    }
