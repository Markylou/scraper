# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python scraping and parsing pipeline for Final Fantasy XIII-2 data. Shared code lives in `src/ffxiii2_scraper/`, with small runnable entry points in `scripts/`. Source inputs live in `inputs/`, cached HTML in `data/raw_html/`, parsed JSON in `data/parsed/monsters/` and `data/parsed/feral_links/`, and JSON schemas in `data/schemas/`. Planning notes belong in `docs/`.

Keep reusable parsing, fetching, path, and naming logic inside `src/ffxiii2_scraper/`; keep `scripts/` as thin command wrappers.

## Build, Test, and Development Commands

Create or update the virtual environment, then install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Common pipeline commands:

```powershell
.\.venv\Scripts\python.exe scripts\parse_index_urls.py
.\.venv\Scripts\python.exe scripts\scrape_fandom_api.py
.\.venv\Scripts\python.exe scripts\scrape_playwright.py
.\.venv\Scripts\python.exe scripts\parse_monsters.py
.\.venv\Scripts\python.exe scripts\parse_feral_links.py
```

`parse_monsters.py` and `parse_feral_links.py` clear and rebuild their respective parsed output directories. Use the API scraper for Fandom wiki pages and the Playwright scraper for pages that need a browser.

## Coding Style & Naming Conventions

Use Python 3.12+ style with 4-space indentation, type hints where they clarify parser contracts, and standard-library imports before third-party imports. Prefer small pure helpers for text cleanup, slug creation, HTML-shape checks, and schema-field parsing.

Use snake_case for modules, functions, and variables. Parsed JSON filenames should use lowercase slugs such as `feral-behemoth.json`. Index/reference HTML uses the `_INDEX_` prefix, for example `data/raw_html/_INDEX_feral_link.html`; normal fetched pages use title-plus-hash filenames.

## Testing Guidelines

There is no formal test suite yet. Before changing parser behavior, run the relevant rebuild command and inspect representative JSON in `data/parsed/`. For broad parser changes, validate both monsters and feral links:

```powershell
.\.venv\Scripts\python.exe scripts\parse_monsters.py
.\.venv\Scripts\python.exe scripts\parse_feral_links.py
```

When adding tests later, place them under `tests/` and name files `test_<module>.py`.

## Commit & Pull Request Guidelines

Git history currently only shows an initial commit, so use concise imperative commit subjects such as `Add feral link parser` or `Fix index page naming`. Keep PRs focused, describe the pipeline stage affected, list verification commands run, and call out regenerated data files or intentionally stale cache changes.

## Agent-Specific Instructions

Do not hand-edit generated parsed JSON unless documenting a fixture. For schema or parser changes, verify against cached or freshly fetched HTML and update schema, parser, and regenerated outputs together.
