# Page Scraper

Small scraping and extraction pipeline for saving web pages and preparing clean content files.

## Project Layout

- `src/page_scraper/`: shared scraper and parser code
- `scripts/`: runnable entry points
- `inputs/page_urls.txt`: generalized seed URLs
- `inputs/monster_urls.txt`: compatibility seed URLs for existing workflows
- `data/pages/`: saved pages organized by URL path
- `data/pages/games/source.html`: original saved HTML for `https://.../Games/`
- `data/pages/games/final-fantasy-x/source.html`: original saved HTML for `https://.../Games/Final-Fantasy-X/`
- Every saved page folder also contains `content.html`, `content.md`, and `metadata.json`
- `docs/pipeline_notes.md`: pipeline planning notes

## Common Commands

From `D:\projects\scraper`:

```powershell
.\.venv\Scripts\python.exe scripts\scrape_fandom_api.py
.\.venv\Scripts\python.exe scripts\scrape_playwright.py
.\.venv\Scripts\python.exe scripts\build_page_content.py
```

## Browser UI

Launch the local browser UI:

```powershell
.\.venv\Scripts\python.exe scripts\launch_ui.py
```

Use **Save pages** to paste one or more page links and let the app choose the best saving method automatically. Each page is saved as a folder under `data/pages/` that mirrors the URL path, with the original HTML, clean content HTML, Markdown, and metadata together.

Use **Refresh content files** if you want to rebuild `content.html`, `content.md`, and `metadata.json` from the already saved `source.html` files. Refresh does not download pages again.

Technical notes:

- Final Fantasy Fandom wiki URLs use the existing Fandom API scraper.
- Other URLs use a generalized requests-based scraper first.
- If a page appears to need a browser, the app falls back to Playwright automatically.
- Saved page folders go to `data/pages/`.
- The full original HTML is always preserved as `source.html`.
- The Markdown is a transform of the cleaned content HTML; it does not replace the raw source.
- URL path segments become nested folder names. For example, `https://jegged.com/Games/Final-Fantasy-X/Abilities/` saves to `data/pages/games/final-fantasy-x/abilities/`.

## Notes

- `scripts/scrape_fandom_api.py` fetches Final Fantasy Fandom wiki pages through the MediaWiki API and writes page folders into `data/pages/`.
- `scripts/scrape_playwright.py` fetches general web pages through a headless browser and writes page folders into `data/pages/`.
- `scripts/build_page_content.py` refreshes content files for every folder in `data/pages/` that contains `source.html`.
