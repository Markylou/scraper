# FFXIII-2 Scraper

Small scraping and extraction pipeline for Final Fantasy XIII-2 wiki monster data.

## Project Layout

- `src/ffxiii2_scraper/`: shared scraper and parser code
- `scripts/`: runnable entry points
- `inputs/monster_urls.txt`: seed URLs
- `data/raw_html/`: cached raw page HTML
- `data/parsed/monsters/`: parsed monster JSON
- `data/parsed/feral_links/`: parsed feral link JSON
- `data/schemas/`: JSON schemas
- `docs/pipeline_notes.md`: pipeline planning notes

## Common Commands

From `D:\projects\scraper`:

```powershell
.\.venv\Scripts\python.exe scripts\parse_index_urls.py
.\.venv\Scripts\python.exe scripts\scrape_api.py
.\.venv\Scripts\python.exe scripts\scrape_playwright.py
.\.venv\Scripts\python.exe scripts\parse_monsters.py
.\.venv\Scripts\python.exe scripts\parse_feral_links.py
```

## Notes

- `scripts/parse_index_urls.py` rebuilds `inputs/monster_urls.txt` from the cached Paradigm Pack index page.
- `scripts/scrape_api.py` is the normal fetch step for wiki HTML and writes files into `data/raw_html/`.
- `scripts/parse_monsters.py` clears `data/parsed/monsters/` and rebuilds the parsed JSON from the cached raw HTML.
- `scripts/parse_feral_links.py` clears `data/parsed/feral_links/` and rebuilds feral-link records from `data/raw_html/_INDEX_feral_link.html`.
- The parser skips `_INDEX_*.html` monster-list pages during normal monster extraction.
- The parser also skips cached disambiguation pages so stale fetches do not overwrite real monster outputs.
- Paradigm Pack note text is pulled from each monster page's `Paradigm Pack` section.
- Current output is still a raw/intermediate shape, not a fully normalized relational dataset yet.
