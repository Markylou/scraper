import asyncio
from uuid import uuid4

from playwright.async_api import async_playwright

from .core.job_output import job_output_root
from .io_utils import load_urls
from .page_archive import archive_page
from .page_naming import page_title_from_url
from .paths import PAGE_URLS_FILE, ensure_project_dirs


REQUEST_DELAY_SECONDS = 1


async def fetch_page_html(url: str) -> tuple[str, str]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2000)
        html = await page.content()
        final_url = page.url or url
        await browser.close()
        return final_url, html


async def main() -> None:
    ensure_project_dirs()
    urls = load_urls(PAGE_URLS_FILE)

    print(f"Loaded {len(urls)} URLs")
    if not urls:
        print("Done.")
        return

    pages_dir = job_output_root(urls[0], uuid4().hex) / "pages"

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        for i, url in enumerate(urls, start=1):
            try:
                print(f"[{i}/{len(urls)}] Fetching: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(2000)

                html = await page.content()
                title = page_title_from_url(page.url or url)
                archive = archive_page(
                    url=url,
                    final_url=page.url or url,
                    title=title,
                    html=html,
                    strategy="browser",
                    pages_dir=pages_dir,
                )

                print(f"  Saved: {archive.folder.name}")
                await asyncio.sleep(REQUEST_DELAY_SECONDS)
            except Exception as exc:
                print(f"  Failed: {url}")
                print(f"  Error: {exc}")

        await browser.close()

    print("Done.")
