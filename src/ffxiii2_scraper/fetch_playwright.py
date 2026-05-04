import asyncio

from playwright.async_api import async_playwright

from .io_utils import load_urls
from .page_naming import page_title_from_url, safe_filename_from_title
from .paths import MONSTER_URLS_FILE, RAW_HTML_DIR, ensure_project_dirs


REQUEST_DELAY_SECONDS = 1

async def main() -> None:
    ensure_project_dirs()
    urls = load_urls(MONSTER_URLS_FILE)

    print(f"Loaded {len(urls)} URLs")

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
                output_path = RAW_HTML_DIR / safe_filename_from_title(title, html)
                output_path.write_text(html, encoding="utf-8")

                print(f"  Saved: {output_path.name}")
                await asyncio.sleep(REQUEST_DELAY_SECONDS)
            except Exception as exc:
                print(f"  Failed: {url}")
                print(f"  Error: {exc}")

        await browser.close()

    print("Done.")
