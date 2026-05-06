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

## Browser UI + API

Launch the local server (FastAPI backend):

```powershell
.\.venv\Scripts\python.exe scripts\launch_ui.py
```

The server runs at **http://127.0.0.1:8765**

- **Interactive API docs**: http://127.0.0.1:8765/docs (best place to explore)
- **ReDoc**: http://127.0.0.1:8765/redoc

### What the UI / API supports
- Paste URLs → **Save pages** (creates job + writes `data/jobs/<site>_<id>/pages/...`)
- **Find pages** (crawler with depth + domain/path limits)
- **Download selected** pages + assets
- Image variant selection for responsive images
- Pause / Resume / Cancel running jobs
- Retry failed downloads
- Refresh derived `content.html` / `content.md` / `metadata.json`

### Technical notes
- Final Fantasy Fandom wiki URLs use the fast Fandom API path.
- Other sites use `requests` first, with automatic Playwright fallback when needed.
- All output goes under `data/jobs/<site>_<short-job-id>/`
- Page folders mirror the URL path structure for easy browsing.
- Job state is in-memory (fast). Completed work is persisted as files + `manifest.json`.
- The old custom HTTP server has been replaced with FastAPI for better docs, validation, and maintainability.

## Notes

- `scripts/build_page_content.py` refreshes content files for every job page folder under `data/jobs/*/pages/` that contains `source.html`.
- Logs are for debugging server, crawler, and downloader behavior. User-facing job progress still lives in API events, failures, and `manifest.json`.

## Local API

The local server exposes a JSON API at `http://127.0.0.1:8765/api/...` for future local frontends. It supports explicit page saves, crawler jobs, selection updates, image variant selection, downloads, job polling, events, failures, and manifest access.

The API is intentionally local and in-memory for now. Restarting the server clears active job state, but downloaded output remains in `data/jobs/<site>_<job-id>/`.

See `docs/api.md` for the current route contract.
