# Repository Guidelines

## Project Structure & Module Organization

This repository is a generalized local Python page-scraper backend. Shared code lives in `src/page_scraper/`, with small runnable entry points in `scripts/`. Source URL inputs live in `inputs/`, with `inputs/page_urls.txt` as the preferred generalized input and `inputs/monster_urls.txt` kept only as compatibility/sample data.

All normal saved output lives under `data/jobs/`. Each job folder is named from the source site plus a short job id, for example `data/jobs/jegged_abcdef12/`, and contains `manifest.json`. Saved pages live inside the job `pages/` folder with URL-path folders; each page folder contains `source.html`, `content.html`, `content.md`, and `metadata.json`. Crawler downloads may also include `assets/`. Planning notes belong in `docs/`, especially `docs/superpowers/plans/`.

Keep reusable normalization, fetching, crawling, archiving, job, and manifest logic inside `src/page_scraper/`; keep `scripts/` as thin command wrappers.

## Build, Test, and Development Commands

Create or update the virtual environment, then install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Common commands:

```powershell
.\.venv\Scripts\python.exe scripts\launch_ui.py
.\.venv\Scripts\python.exe scripts\build_page_content.py
.\.venv\Scripts\python.exe scripts\scrape_fandom_api.py
.\.venv\Scripts\python.exe scripts\scrape_playwright.py
```

Use **Save pages** in the UI for explicit URLs. Use **Find pages** / **Download selected** for crawler-style jobs. Use **Refresh content files** to rebuild derived files from existing `source.html` without downloading from the web.

## Coding Style & Naming Conventions

Use Python 3.12+ style with 4-space indentation, type hints where they clarify contracts, and standard-library imports before third-party imports. Prefer small pure helpers for URL normalization, folder planning, text cleanup, HTML extraction, asset classification, and manifest summaries.

Use snake_case for modules, functions, and variables. Generated page archive folders should mirror normalized URL path segments inside a job, for example `data/jobs/jegged_abcdef12/pages/games/final-fantasy-x/abilities/`.

## Testing Guidelines

Keep tests under `tests/` and name files `test_<module>.py`. Before changing scraper behavior, run the focused manual test runner used in this repo or an equivalent `pytest` command when available. Broad backend changes should verify URL normalization, job store behavior, archive writing, crawler discovery, asset discovery, downloader output, manifests, and the existing Save Pages UI/API flow.

## Agent-Specific Instructions

Do not revive the old page-record/reference-record/monster parser workflow unless the user explicitly asks for a specialized extraction pipeline. The current source of truth for saved pages is `source.html` plus rebuildable derived files and, for job downloads, `manifest.json`.
