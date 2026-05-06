# Page Scraper

Small scraping and extraction pipeline for saving web pages and preparing clean content files.

## Project Layout

- `src/page_scraper/`: shared scraper and parser code
- `scripts/`: runnable entry points
- `inputs/page_urls.txt`: generalized seed URLs
- `inputs/monster_urls.txt`: compatibility seed URLs for existing workflows
- `data/jobs/`: all saved output, grouped by site slug and job id
- `data/jobs/jegged_<job-id>/pages/games/source.html`: original saved HTML for `https://jegged.com/Games/`
- `data/jobs/jegged_<job-id>/pages/games/final-fantasy-x/source.html`: original saved HTML for `https://jegged.com/Games/Final-Fantasy-X/`
- Every saved page folder also contains `content.html`, `content.md`, and `metadata.json`
- Job folders can also contain `assets/` and always include `manifest.json`
- `src/page_scraper/core/`: backend engine modules for normalization, discovery, asset detection, downloading, and manifests
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

Use **Save pages** to paste one or more page links and let the app choose the best saving method automatically. Each save creates a folder under `data/jobs/`, then stores pages inside that job's `pages/` folder using the URL path.

Use **Refresh content files** if you want to rebuild `content.html`, `content.md`, and `metadata.json` from the already saved `source.html` files. Refresh does not download pages again.

Use **Find pages** to start from one page and discover nearby pages/files. Use **Download selected** to save the discovered selection under `data/jobs/`.

Technical notes:

- Final Fantasy Fandom wiki URLs use the existing Fandom API scraper.
- Other URLs use a generalized requests-based scraper first.
- If a page appears to need a browser, the app falls back to Playwright automatically.
- Saved page folders go to `data/jobs/<site>_<job-id>/pages/`.
- The full original HTML is always preserved as `source.html`.
- The Markdown is a transform of the cleaned content HTML; it does not replace the raw source.
- URL path segments become nested folder names. For example, `https://jegged.com/Games/Final-Fantasy-X/Abilities/` saves to `data/jobs/jegged_<job-id>/pages/games/final-fantasy-x/abilities/`.
- Job output folders are isolated under `data/jobs/<site>_<job-id>/` and include a portable `manifest.json`.
- Job state is intentionally in memory for now; SQLite persistence is not part of this phase.
- Developer logs are written to `logs/page_scraper.log` when the local UI server runs.

## Notes

- `scripts/build_page_content.py` refreshes content files for every job page folder under `data/jobs/*/pages/` that contains `source.html`.
- Logs are for debugging server, crawler, and downloader behavior. User-facing job progress still lives in API events, failures, and `manifest.json`.

## Local API

The local server exposes a JSON API at `http://127.0.0.1:8765/api/...` for future local frontends. It supports explicit page saves, crawler jobs, selection updates, image variant selection, downloads, job polling, events, failures, and manifest access.

The API is intentionally local and in-memory for now. Restarting the server clears active job state, but downloaded output remains in `data/jobs/<site>_<job-id>/`.

See `docs/api.md` for the current route contract.
