# Local Backend Engine Without SQLite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local backend engine on top of the current `page_scraper` package with crawl discovery, asset discovery, job-isolated output, manifests, structured events/failures, and simple UI/API controls, without SQLite persistence.

**Architecture:** Keep the current Python package, simple HTTP server, and explicit Save Pages flow. Add core backend modules under `src/page_scraper/core/`, expand the in-memory `JobStore`, and use `data/jobs/<source>_<job-id>/` for job output while preserving `data/pages/` for direct saves.

**Tech Stack:** Python 3.12, standard-library HTTP server, `requests`, Playwright fallback, BeautifulSoup/lxml, filesystem manifests, in-memory job state.

---

### Task 1: Clean Current Docs and Naming Drift

- [ ] Update `AGENTS.md`, `README.md`, and `Documentation.md` so `src/page_scraper/`, `data/pages/`, URL-tree archives, and `inputs/page_urls.txt` are described as the current model.
- [ ] Mark `inputs/monster_urls.txt` as compatibility/sample input only.
- [ ] Keep old page-record/reference-record/monster parser flows out of active instructions.

### Task 2: Add Core URL Normalization and Boundary Rules

- [ ] Create `src/page_scraper/core/normalizer.py`.
- [ ] Implement URL normalization, identity keys, supported-scheme filtering, same-domain checks, and same-start-path checks.
- [ ] Add unit tests for relative URLs, fragments, unsupported schemes, domains, start paths, query strings, and duplicate identities.

### Task 3: Add In-Memory Job Model and Structured Events

- [ ] Expand `src/page_scraper/job_store.py` with job statuses, events, failures, pages, assets, and pause/resume/cancel flags.
- [ ] Preserve compatibility for existing `/api/jobs/{job_id}` polling, including `messages`, `done`, and `error`.
- [ ] Add tests for job lifecycle, events, failures, selections, pause/resume/cancel, and old scrape compatibility.

### Task 4: Add Job Output Folders

- [ ] Add `JOBS_DIR = DATA_DIR / "jobs"` to `paths.py`.
- [ ] Add folder planning for `data/jobs/<source-slug>_<short-job-id>/`.
- [ ] Allow `archive_page()` to write under `data/jobs/<job>/pages/...`.
- [ ] Keep explicit Save Pages writing to `data/pages/...`.

### Task 5: Formalize Fetch Results

- [ ] Expand `FetchResult` with requested URL, final URL, status code, content type, body bytes, text, and fetch strategy.
- [ ] Preserve existing `url` and `html` aliases for compatibility.
- [ ] Keep the UTF-8-vs-Latin-1 decoding guard.

### Task 6: Add Discovery Settings and Crawler

- [ ] Create `src/page_scraper/core/crawler.py`.
- [ ] Add `DiscoverySettings` with max-depth, domain/path boundary, include flags, and Playwright fallback defaults.
- [ ] Discover pages from one start URL, apply boundaries, dedupe URLs, record pages/assets, and emit events/failures.

### Task 7: Add Asset Discovery

- [ ] Create `src/page_scraper/core/asset_discovery.py`.
- [ ] Detect `img[src]`, `img[data-src]`, basic `srcset`, and document/media links.
- [ ] Classify assets as image, document, video, audio, or other.
- [ ] Select images/documents by default and skip video/audio by default.

### Task 8: Add Downloader

- [ ] Create `src/page_scraper/core/downloader.py`.
- [ ] Download selected pages to `data/jobs/<job>/pages/...`.
- [ ] Download selected assets to `assets/images/`, `assets/documents/`, or `assets/other/`.
- [ ] Use deterministic `<slug>-<short-hash>.<ext>` asset filenames.
- [ ] Respect pause, resume, and cancel flags at queue boundaries.

### Task 9: Add Manifest Writer

- [ ] Create `src/page_scraper/core/manifest.py`.
- [ ] Write `manifest.json` with job metadata, settings, summary counts, output paths, and structured failures.
- [ ] Treat the manifest as portable output metadata, not app persistence.

### Task 10: Add Dev UI/API Controls

- [ ] Keep existing save and refresh endpoints.
- [ ] Add job creation, discovery, selection, download, pause/resume/cancel, events, failures, and manifest endpoints.
- [ ] Add simple UI controls using non-technical labels: Find pages, Choose what to save, Download selected, Pause, Resume, Cancel.

### Verification

- [ ] Existing manual test runner returns `manual tests passed`.
- [ ] Import check returns `imports ok`.
- [ ] Existing Save Pages UI/API flow still saves the first ten `inputs/monster_urls.txt` URLs.
- [ ] Discovery from `https://jegged.com/Games/Final-Fantasy-X/` records bounded pages/assets.
- [ ] Download selected writes a job folder under `data/jobs/` with page archives, assets, and `manifest.json`.
