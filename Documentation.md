# Implementation Log

## 2026-05-04

- Started executing `docs/superpowers/plans/2026-05-04-browser-scraper-ui.md`.
- Reviewed the existing repo state before edits. The worktree already had unrelated modified/deleted files, especially many deleted files under `data/raw_html/`; those are being left alone unless required for verification.
- Created feature branch `codex-browser-scraper-ui` after the slash-style branch name could not be created in this environment.
- Adjusted execution detail for the input URL file: keep `inputs/monster_urls.txt` available because the done condition explicitly names it, while adding the generalized `inputs/page_urls.txt` for the UI path.
- Generalized non-Fandom names: moved the Python package to `src/page_scraper/`, renamed parser scripts to `build_page_records.py` and `build_reference_records.py`, and moved generated output directories to `data/parsed/page_records/` and `data/parsed/reference_records/`.
- Added reusable service modules: `url_utils.py`, `fetch_requests.py`, `scrape_service.py`, and `job_store.py`.
- Added the local browser UI server in `src/page_scraper/ui_server.py`, browser assets in `src/page_scraper/ui/`, and launch wrapper `scripts/launch_ui.py`.
- Added focused tests under `tests/`. `pytest` could not be installed because `pip` hit Windows permission errors while unpacking wheels, so I verified the tests with a manual Python runner using the same test functions.
- Verified imports with `PYTHONDONTWRITEBYTECODE=1` because existing `__pycache__` directories reject bytecode writes in this environment.
- Adjusted output directories after verification found Windows write denial inside `data/raw_html/` and `data/parsed/`. New scraper output now uses writable generalized folders: `data/saved_pages/`, `data/page_records/`, and `data/reference_records/`.
- Re-ran manual tests successfully after path changes.
- Ran `scripts/build_page_records.py`; it completed and reported `Found 0 HTML files`, which is expected before any pages are saved to `data/saved_pages/`.
- Ran `scripts/build_reference_records.py`; it failed because `_INDEX_feral_link.html` is not present in either the new saved-pages folder or the legacy raw HTML cache. This is a missing source-input issue, not a UI scrape blocker.
- Verified the local UI/API path in-process on `http://127.0.0.1:8876`: submitted the first ten links from `inputs/monster_urls.txt` to `/api/scrape`, the job completed with `SAVED_COUNT 10` and `FAILED_COUNT 0`, and the ten HTML files were written to `data/saved_pages/`.
- Re-ran `scripts/build_page_records.py` after the UI scrape; it found 10 saved HTML files and produced page records in `data/page_records/`.
- Added local verification artifacts (`.tmp/`, `.codex/`, `server.*`, `envtest.*`) to `.gitignore`; deletion was blocked by the current approval policy, so they are ignored rather than staged.
- Repaired `.venv/pyvenv.cfg` so `.\.venv\Scripts\python.exe` runs again in this environment and reports Python 3.12.13.
- Attempted to install `pytest` through the repaired venv, but `pip` still failed with a Windows permission error while unpacking to a temp directory. Added `tmp/` to `.gitignore` for those pip scratch files.
- Final verification with repaired `.venv`:
  - `.\.venv\Scripts\python.exe --version` returned `Python 3.12.13`.
  - Manual test runner returned `manual tests passed`.
  - In-process UI/API scrape on `http://127.0.0.1:8877` submitted the first ten `inputs/monster_urls.txt` links and returned `SAVED_COUNT 10` and `FAILED_COUNT 0`.

## 2026-05-04 Page Archive Update

- Replaced the normal page-record workflow with a per-page archive workflow.
- Added `src/page_scraper/page_archive.py` to create one folder per saved page with:
  - `source.html` for the original full HTML.
  - `content.html` for the cleaned main page content.
  - `content.md` for a readable Markdown transform.
  - `metadata.json` for source URL, final URL, title, saved time, file list, image URLs, and links.
- Added `src/page_scraper/content_builder.py` and `scripts/build_page_content.py` so content files can be refreshed from existing `source.html` files.
- Updated the browser UI:
  - `Save pages` now writes page folders under `data/pages/`.
  - `Refresh content files` rebuilds clean content, Markdown, and metadata from saved sources.
  - Removed the normal-user buttons for page records and reference records.
- Updated the Fandom API scraper and Playwright scraper so both write the new page-folder structure.
- Removed unused old parser/build files for page records and reference records.
- Removed old generated/schema artifacts that belonged to the previous page-record/reference-record flow.
- Added a requests decoding guard so pages that are actually UTF-8 do not get decoded as Latin-1 when the server omits charset metadata.
- Updated `.gitignore` for generated page archive folders and old generated output folders.
- Attempted to delete obsolete generated/temp directories directly, but the environment rejected the guarded `Remove-Item` cleanup command. Those directories are now ignored when generated.
- Verification:
  - Manual test runner returned `manual tests passed`.
  - Import check returned `imports ok`.
  - In-process UI/API scrape on `http://127.0.0.1:8882` submitted the first ten `inputs/monster_urls.txt` links and returned `SAVED_COUNT 10`, `FAILED_COUNT 0`, `MISSING_COUNT 0`, and `REFRESHED_COUNT 10`.
  - `scripts/build_page_content.py` returned `Refreshed 10 page folder(s)`.

## 2026-05-04 URL Tree Archive Update

- Changed page archive folders to mirror URL path segments instead of flattening the path into one folder name.
- Example: `https://jegged.com/Games/Final-Fantasy-X/Abilities/Equipment/Armor.html` now saves to `data/pages/games/final-fantasy-x/abilities/equipment/armor/`.
- Parent pages and child pages can each have their own files. For example, `data/pages/games/` can contain `source.html`, `content.html`, `content.md`, and `metadata.json` while also containing `final-fantasy-x/`.
- Added query-string handling so URLs with query parameters get a short hash appended to the final path segment.
- Updated content refresh to walk nested page folders and rebuild every folder that contains `source.html`.
- Clarified UX language:
  - `Save pages` downloads or refreshes `source.html` from the web and then rebuilds derived files.
  - `Refresh content files` stays local and rebuilds derived files from existing `source.html` files.
- Verification:
  - Manual test runner returned `manual tests passed`.
  - Import check returned `imports ok`.
  - `scripts/build_page_content.py` returned `Refreshed 10 page folder(s)` before the new nested scrape.
  - In-process UI/API scrape on `http://127.0.0.1:8883` submitted the first ten `inputs/monster_urls.txt` links and returned `SAVED_COUNT 10`, `FAILED_COUNT 0`, and `MISSING_COUNT 0`.
  - The UI/API scrape returned nested paths including `games/final-fantasy-x/abilities/equipment/armor`.
  - UI content refresh rebuilt every expected nested path; it returned `REFRESHED_COUNT 20` because older flat page folders still exist in ignored generated output alongside the new nested folders.

## 2026-05-05 Local Backend Engine Without SQLite

- Saved the implementation plan to `docs/superpowers/plans/2026-05-05-local-backend-engine-no-sqlite.md`.
- Updated `AGENTS.md` so future work uses `src/page_scraper/`, `data/pages/`, `data/jobs/`, and page archive terminology instead of the old FFXIII-2 parser workflow.
- Added `src/page_scraper/core/normalizer.py` for URL normalization, identity keys, supported-scheme checks, same-domain checks, and same-start-path checks.
- Expanded `src/page_scraper/job_store.py` into an in-memory job model with structured events, failures, pages, assets, selection state, and pause/resume/cancel flags while preserving existing `done`/`error` polling compatibility.
- Added `data/jobs/` path support and `src/page_scraper/core/job_output.py` for job output folder planning.
- Expanded request fetch results with requested URL, final URL, status code, content type, body bytes, decoded text, and fetch strategy while preserving `url` and `html` compatibility aliases.
- Added `src/page_scraper/core/asset_discovery.py` for image/document/video/audio/other asset classification and discovery from HTML.
- Added `src/page_scraper/core/crawler.py` with `DiscoverySettings`, bounded page discovery, page/asset recording, event emission, and structured skip/failure records.
- Added `src/page_scraper/core/downloader.py` for sequential selected-page and selected-asset downloads into job folders.
- Added `src/page_scraper/core/manifest.py` to write portable `manifest.json` job summaries.
- Added dev HTTP endpoints for creating jobs, discovery, page/asset lists, selection, download, pause/resume/cancel, events, failures, and manifest access.
- Expanded the simple UI with `Find pages`, `Download selected`, `Pause`, `Resume`, and `Cancel` controls.
- SQLite persistence remains intentionally excluded; active job state is in memory and completed job output is represented by files on disk.
- Verification:
  - Manual test runner returned `manual tests passed`.
  - Import check returned `imports ok`.
  - In-process UI/API scrape on `http://127.0.0.1:8892` submitted the first ten `inputs/monster_urls.txt` links and returned `SAVE_SAVED_COUNT 10`, `SAVE_FAILED_COUNT 0`, and `SAVE_MISSING_COUNT 0`.
  - In-process UI/API discovery from `https://jegged.com/Games/Final-Fantasy-X/` with depth `0` returned `DISCOVERED_PAGES 1` and `DISCOVERED_ASSETS 38`.
  - In-process UI/API download wrote `data/jobs/final-fantasy-x_7adceccf/manifest.json` and returned `MANIFEST_STATUS completed`.

## 2026-05-05 Crawler UI Refinement

- Moved the `Find pages` crawler controls above the plain save form because discovery is now the expected first step.
- Integrated crawler results with the existing page-link textarea:
  - discovered page URLs are written into `Page links to save`;
  - the user can edit that list before saving pages or downloading a crawler job.
- Added a `Links Found: 0` counter that updates from the job polling response while discovery runs.
- Replaced the discovered files bullet list with a table using `Save`, `Type`, and `URL` columns.
- File rows now use checkboxes, checked by default, and checkbox changes are sent to the job selection API.
- Hide the `Pause`, `Resume`, and `Cancel` controls when a crawl is not actively running or has finished.
- Verification:
  - Manual focused tests for asset discovery and job-store selection returned `manual focused tests passed`.
  - Import check returned `imports ok`.
  - Static UI server smoke check returned `200` for `/`, `/app.js`, `/styles.css`, and `/api/health`.
  - In-process UI/API discovery from `https://jegged.com/Games/Final-Fantasy-X` with depth `0` returned `status done`, `pages 1`, and `assets 38`, with discovered assets selected by default.

## 2026-05-05 Unified Job Output

- Made `data/jobs/` the single active output root for UI saves and crawler downloads.
- Changed job folder naming to use the source site's root domain without the TLD plus the short job id:
  - `https://jegged.com/Games/Final-Fantasy-X/` saves under `data/jobs/jegged_<job-id>/`.
  - `https://guides.gamercorner.net/ffxiii-2/weapons/` saves under `data/jobs/gamercorner_<job-id>/`.
- Updated `Save pages` so pasted URLs create a job folder and write pages under `data/jobs/<site>_<job-id>/pages/`.
- Kept the URL-path page archive structure inside each job's `pages/` folder.
- Updated saved page UI output to show `data/jobs/.../pages/.../source.html` paths instead of `data/pages/...`.
- Updated content refresh so the default command walks `data/jobs/*/pages/`.
- Updated docs to describe `data/jobs/` as the active output model and `manifest.json` as the per-job summary.
- Cleaned generated test-run data and removed obsolete output directories from `data/`; only `data/jobs/` remains.
- Verification:
  - Manual all-test runner passed `33` test functions.
  - UI/API `Save pages` smoke test wrote to `data/jobs/jegged_<job-id>/pages/...` and returned a job `output_root`.
  - Repo docs and active scripts no longer reference `data/pages/`, old raw HTML caches, page records, reference records, or saved-pages folders as active output.

## 2026-05-05 Source/Test Stale File Cleanup

- Reviewed `src/page_scraper/` and `tests/` for leftover parser, design, cache, and compatibility artifacts.
- Removed the unused UI concept file `src/page_scraper/ui/page-saver-design.html`.
- Removed generated `__pycache__/` folders from `src/page_scraper/`, `src/page_scraper/core/`, and `tests/`.
- Removed stale path compatibility constants for the old raw-HTML and monster-parser flow.
- Removed default `data/pages/` write targets from archive/scrape helpers so active save paths must be job-owned.
- Updated the package docstring from the old FFXIII-2-specific wording to generalized page scraping.
