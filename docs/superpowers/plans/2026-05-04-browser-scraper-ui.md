# Browser Scraper UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a simple local browser UI that lets a non-technical user paste page URLs, start scraping, and run the existing build steps without choosing low-level scraper commands.

**Architecture:** First rename non-Fandom files and directories that are specific to FFXIII-2 or a single site into generalized names. Then add a small standard-library Python web server that serves a minimal HTML/CSS/JS interface and exposes JSON endpoints for scrape and build jobs. Move scraper selection into reusable service code: preserve the existing Fandom API module, add a generalized `requests` fetcher, and use Playwright automatically when a normal HTTP fetch is not enough.

**Tech Stack:** Python 3.12+, standard-library `http.server`, `threading`, `webbrowser`, existing `requests`, `beautifulsoup4`, `lxml`, and `playwright`; plain HTML/CSS/JavaScript for the browser UI.

---

## File Structure

- Rename `src/ffxiii2_scraper/` to `src/page_scraper/`: generalized package name for the reusable scraping pipeline.
- Rename `inputs/monster_urls.txt` to `inputs/page_urls.txt`: generalized pasted/fetched page URL list.
- Rename `data/parsed/monsters/` to `data/parsed/page_records/`: generalized extracted page records.
- Rename `data/parsed/feral_links/` to `data/parsed/reference_records/`: generalized extracted index/reference-table records.
- Keep `src/page_scraper/fetch_fandom_api.py` and `scripts/scrape_fandom_api.py` explicitly Fandom-specific; this is the one naming exception.
- Rename `src/page_scraper/monster_parser.py` to `src/page_scraper/page_record_parser.py`.
- Rename `src/page_scraper/feral_link_parser.py` to `src/page_scraper/reference_record_parser.py`.
- Rename `scripts/parse_monsters.py` to `scripts/build_page_records.py`.
- Rename `scripts/parse_feral_links.py` to `scripts/build_reference_records.py`.
- Create `src/page_scraper/url_utils.py`: URL cleanup, validation, de-duplication, and domain classification.
- Create `src/page_scraper/fetch_requests.py`: generalized HTTP fetcher using `requests.get`; no Fandom-specific API behavior.
- Create `src/page_scraper/scrape_service.py`: automatic strategy selection, progress reporting, output writing, and scrape result summaries.
- Create `src/page_scraper/job_store.py`: tiny in-memory background job registry for UI progress.
- Create `src/page_scraper/ui_server.py`: local HTTP server, API routes, background job launch, and browser opening.
- Create `src/page_scraper/ui/index.html`: single-screen UI.
- Create `src/page_scraper/ui/styles.css`: clean, minimal visual design.
- Create `src/page_scraper/ui/app.js`: browser-side form handling, progress polling, and plain-language status updates.
- Create `scripts/launch_ui.py`: thin entry point for opening the local UI.
- Modify `src/page_scraper/fetch_playwright.py`: expose a reusable `fetch_page_html(url)` helper while keeping the existing CLI behavior.
- Modify `src/page_scraper/fetch_fandom_api.py`: expose a reusable `fetch_fandom_url(url)` helper while preserving `scripts/scrape_fandom_api.py`.
- Modify `src/page_scraper/paths.py`: add generalized path constants and `UI_DIR`.
- Modify `README.md`: add the non-technical UI launch command and explain what the UI does.
- Create tests under `tests/` for URL cleanup, scraper selection, generalized requests fallback decisions, and job state transitions.

## Generalized Naming Rules

- Keep `fandom` in filenames and labels only where the code truly uses the Fandom API.
- Avoid new file or directory names containing `ffxiii2`, `finalfantasy`, `monster`, `feral_link`, `jegged`, or another game/site-specific concept unless the file is a legacy parser fixture or a Fandom API integration.
- Use generalized user-facing terms:
  - `page records` for extracted page JSON.
  - `reference records` for index/table-derived JSON.
  - `saved pages` for cached HTML.
  - `build` instead of `parse` in the UI.
  - `page URLs` instead of `monster URLs`.

## UX Language

Use plain language throughout the UI:

- Textbox label: `Paste page links`
- Primary button: `Save pages`
- Empty-state helper: `Paste one page link per line. The app will choose the best way to save each page.`
- Progress label: `Saving pages...`
- Success label: `Saved page files`
- Build buttons: `Build page records` and `Build reference records`
- Technical details disclosure: `Show details`
- Error summary: `Some pages could not be saved`

Avoid exposing terms like API, Playwright, schema, cache, HTTP status, traceback, or raw HTML in the primary UI. Put technical details behind `Show details`.

## Task 1: Generalize Non-Fandom Names

**Files:**
- Move: `src/ffxiii2_scraper/` -> `src/page_scraper/`
- Move: `inputs/monster_urls.txt` -> `inputs/page_urls.txt`
- Move: `data/parsed/monsters/` -> `data/parsed/page_records/`
- Move: `data/parsed/feral_links/` -> `data/parsed/reference_records/`
- Move: `src/page_scraper/monster_parser.py` -> `src/page_scraper/page_record_parser.py`
- Move: `src/page_scraper/feral_link_parser.py` -> `src/page_scraper/reference_record_parser.py`
- Move: `scripts/parse_monsters.py` -> `scripts/build_page_records.py`
- Move: `scripts/parse_feral_links.py` -> `scripts/build_reference_records.py`
- Modify: `scripts/*.py`
- Modify: `src/page_scraper/*.py`
- Modify: `README.md`
- Test: existing script smoke checks

- [ ] **Step 1: Move package and data paths**

Run:

```powershell
Move-Item -LiteralPath src\ffxiii2_scraper -Destination src\page_scraper
Move-Item -LiteralPath inputs\monster_urls.txt -Destination inputs\page_urls.txt
Move-Item -LiteralPath data\parsed\monsters -Destination data\parsed\page_records
Move-Item -LiteralPath data\parsed\feral_links -Destination data\parsed\reference_records
```

Expected: the package and generated-output directories now have generalized names.

- [ ] **Step 2: Move parser modules and script wrappers**

Run:

```powershell
Move-Item -LiteralPath src\page_scraper\monster_parser.py -Destination src\page_scraper\page_record_parser.py
Move-Item -LiteralPath src\page_scraper\feral_link_parser.py -Destination src\page_scraper\reference_record_parser.py
Move-Item -LiteralPath scripts\parse_monsters.py -Destination scripts\build_page_records.py
Move-Item -LiteralPath scripts\parse_feral_links.py -Destination scripts\build_reference_records.py
```

Expected: only Fandom-specific files keep a specific integration name.

- [ ] **Step 3: Update imports and path constants**

In every moved script, change imports from `ffxiii2_scraper` to `page_scraper`.

In `src/page_scraper/paths.py`, use these generalized constants:

```python
PAGE_URLS_FILE = INPUTS_DIR / "page_urls.txt"
PARSED_PAGE_RECORDS_DIR = PARSED_DIR / "page_records"
PARSED_REFERENCE_RECORDS_DIR = PARSED_DIR / "reference_records"
REFERENCE_INDEX_FILE = RAW_HTML_DIR / "_INDEX_feral_link.html"
PAGE_RAW_SCHEMA_FILE = SCHEMAS_DIR / "monster.raw.schema.json"
REFERENCE_RAW_SCHEMA_FILE = SCHEMAS_DIR / "feral_link.raw.schema.json"
```

Keep `REFERENCE_INDEX_FILE`, `PAGE_RAW_SCHEMA_FILE`, and `REFERENCE_RAW_SCHEMA_FILE` pointing at the existing data files for now so this task is a naming migration, not a schema redesign.

Update `ensure_project_dirs()` to create `PARSED_PAGE_RECORDS_DIR` and `PARSED_REFERENCE_RECORDS_DIR`.

- [ ] **Step 4: Update parser module imports**

In `src/page_scraper/page_record_parser.py`, import generalized path constants:

```python
from .paths import PARSED_PAGE_RECORDS_DIR, RAW_HTML_DIR, PAGE_RAW_SCHEMA_FILE
```

In `src/page_scraper/reference_record_parser.py`, import generalized path constants:

```python
from .paths import PARSED_REFERENCE_RECORDS_DIR, REFERENCE_INDEX_FILE, REFERENCE_RAW_SCHEMA_FILE
```

Keep internal JSON field names unchanged in this task.

- [ ] **Step 5: Update script wrappers**

`scripts/build_page_records.py` should import:

```python
from page_scraper.page_record_parser import main
```

`scripts/build_reference_records.py` should import:

```python
from page_scraper.reference_record_parser import main
```

`scripts/scrape_fandom_api.py`, `scripts/scrape_playwright.py`, and `scripts/parse_index_urls.py` should import from `page_scraper`.

- [ ] **Step 6: Smoke check renamed commands**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\build_page_records.py
.\.venv\Scripts\python.exe scripts\build_reference_records.py
```

Expected: both commands finish successfully and rebuild generalized output directories.

- [ ] **Step 7: Commit**

```powershell
git add src scripts inputs data README.md
git commit -m "Generalize scraper package and output names"
```

## Task 2: Add URL Cleanup And Classification

**Files:**
- Create: `src/page_scraper/url_utils.py`
- Test: `tests/test_url_utils.py`

- [ ] **Step 1: Write URL utility tests**

Create `tests/test_url_utils.py`:

```python
from page_scraper.url_utils import classify_url, normalize_pasted_urls


def test_normalize_pasted_urls_accepts_lines_commas_and_duplicates():
    raw = """
    https://example.com/a
    https://example.com/a, https://example.com/b
    not-a-url
    """

    urls, rejected = normalize_pasted_urls(raw)

    assert urls == ["https://example.com/a", "https://example.com/b"]
    assert rejected == ["not-a-url"]


def test_classify_finalfantasy_fandom_wiki_url():
    assert classify_url("https://finalfantasy.fandom.com/wiki/Chichu") == "fandom"


def test_classify_general_https_url():
    assert classify_url("https://jegged.com/Games/Final-Fantasy-XIII-2/") == "general"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_url_utils.py -v
```

Expected: FAIL because `page_scraper.url_utils` does not exist yet. If `pytest` is missing, add `pytest` to `requirements.txt`, install requirements, and rerun.

- [ ] **Step 3: Implement URL utilities**

Create `src/page_scraper/url_utils.py`:

```python
from urllib.parse import urlparse


def normalize_pasted_urls(raw_text: str) -> tuple[list[str], list[str]]:
    seen: set[str] = set()
    urls: list[str] = []
    rejected: list[str] = []

    candidates = raw_text.replace(",", "\n").splitlines()
    for candidate in candidates:
        value = candidate.strip()
        if not value:
            continue
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            rejected.append(value)
            continue
        normalized = value.rstrip()
        if normalized not in seen:
            seen.add(normalized)
            urls.append(normalized)

    return urls, rejected


def classify_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path
    if host == "finalfantasy.fandom.com" and path.startswith("/wiki/"):
        return "fandom"
    return "general"
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_url_utils.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src\page_scraper\url_utils.py tests\test_url_utils.py requirements.txt
git commit -m "Add URL normalization helpers"
```

## Task 3: Add A Generalized Requests Fetcher

**Files:**
- Create: `src/page_scraper/fetch_requests.py`
- Test: `tests/test_fetch_requests.py`

- [ ] **Step 1: Write tests for fetch result quality**

Create `tests/test_fetch_requests.py`:

```python
from page_scraper.fetch_requests import FetchResult, html_needs_browser


def test_html_needs_browser_when_page_is_too_small():
    assert html_needs_browser("<html></html>") is True


def test_html_needs_browser_when_common_javascript_shell_is_present():
    html = "<html><body><noscript>Please enable JavaScript</noscript></body></html>"
    assert html_needs_browser(html) is True


def test_html_does_not_need_browser_when_content_has_real_body_text():
    html = "<html><head><title>Guide</title></head><body><main>" + ("Useful text " * 80) + "</main></body></html>"
    assert html_needs_browser(html) is False


def test_fetch_result_shape():
    result = FetchResult(url="https://example.com", final_url="https://example.com", html="<html></html>", status_code=200)
    assert result.url == "https://example.com"
    assert result.status_code == 200
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_fetch_requests.py -v
```

Expected: FAIL because `fetch_requests.py` does not exist.

- [ ] **Step 3: Implement generalized requests fetcher**

Create `src/page_scraper/fetch_requests.py`:

```python
from dataclasses import dataclass

import requests


USER_AGENT = "WikiScraper/0.1 (local research tool)"
REQUEST_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class FetchResult:
    url: str
    final_url: str
    html: str
    status_code: int


def fetch_url(url: str) -> FetchResult:
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return FetchResult(
        url=url,
        final_url=response.url,
        html=response.text,
        status_code=response.status_code,
    )


def html_needs_browser(html: str) -> bool:
    compact = " ".join(html.lower().split())
    if len(compact) < 500:
        return True
    browser_markers = [
        "please enable javascript",
        "enable javascript to continue",
        "you need to enable javascript",
        "checking your browser",
        "__next_data__",
    ]
    return any(marker in compact for marker in browser_markers)
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_fetch_requests.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src\page_scraper\fetch_requests.py tests\test_fetch_requests.py
git commit -m "Add generalized requests fetcher"
```

## Task 4: Expose Reusable Fandom And Playwright Helpers

**Files:**
- Modify: `src/page_scraper/fetch_fandom_api.py`
- Modify: `src/page_scraper/fetch_playwright.py`

- [ ] **Step 1: Add reusable Fandom helper without changing CLI behavior**

Modify `src/page_scraper/fetch_fandom_api.py` to add:

```python
def fetch_fandom_url(url: str) -> tuple[str, str]:
    title = page_title_from_url(url)
    html = fetch_parsed_html(title)
    resolved_title = resolve_disambiguation_title(html)
    if resolved_title and resolved_title != title:
        title = resolved_title
        html = fetch_parsed_html(title)
    return title, html
```

Then update `main()` to call `fetch_fandom_url(url)` instead of duplicating the same sequence inline.

- [ ] **Step 2: Add reusable Playwright single-page helper**

Modify `src/page_scraper/fetch_playwright.py` to add:

```python
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
```

Keep the existing `main()` loop intact except for using the helper where it reduces duplication.

- [ ] **Step 3: Smoke check existing script entry points**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\scrape_fandom_api.py
```

Expected: existing Fandom scraping behavior still runs and writes cached HTML.

Run:

```powershell
.\.venv\Scripts\python.exe scripts\scrape_playwright.py
```

Expected: existing Playwright scraping behavior still runs and writes cached HTML.

- [ ] **Step 4: Commit**

```powershell
git add src\page_scraper\fetch_fandom_api.py src\page_scraper\fetch_playwright.py
git commit -m "Expose reusable scraper helpers"
```

## Task 5: Add Automatic Scrape Service

**Files:**
- Create: `src/page_scraper/scrape_service.py`
- Test: `tests/test_scrape_service.py`

- [ ] **Step 1: Write strategy selection tests**

Create `tests/test_scrape_service.py`:

```python
from page_scraper.scrape_service import choose_strategy


def test_choose_strategy_uses_fandom_for_finalfantasy_fandom_wiki():
    assert choose_strategy("https://finalfantasy.fandom.com/wiki/Chichu") == "fandom"


def test_choose_strategy_uses_requests_first_for_general_url():
    assert choose_strategy("https://jegged.com/Games/Final-Fantasy-XIII-2/") == "requests"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_scrape_service.py -v
```

Expected: FAIL because `scrape_service.py` does not exist.

- [ ] **Step 3: Implement scrape service**

Create `src/page_scraper/scrape_service.py`:

```python
import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from .fetch_fandom_api import fetch_fandom_url
from .fetch_playwright import fetch_page_html
from .fetch_requests import fetch_url, html_needs_browser
from .page_naming import page_title_from_url, safe_filename_from_title
from .paths import RAW_HTML_DIR, ensure_project_dirs
from .url_utils import classify_url


ProgressCallback = Callable[[str], None]


@dataclass(frozen=True)
class ScrapeOutcome:
    url: str
    strategy: str
    saved_file: str | None
    ok: bool
    message: str


def choose_strategy(url: str) -> str:
    if classify_url(url) == "fandom":
        return "fandom"
    return "requests"


def scrape_urls(urls: list[str], progress: ProgressCallback | None = None) -> list[ScrapeOutcome]:
    ensure_project_dirs()
    outcomes: list[ScrapeOutcome] = []

    for index, url in enumerate(urls, start=1):
        if progress:
            progress(f"Saving page {index} of {len(urls)}")
        try:
            outcome = scrape_one_url(url)
        except Exception as exc:
            outcome = ScrapeOutcome(url=url, strategy="unknown", saved_file=None, ok=False, message=str(exc))
        outcomes.append(outcome)

    return outcomes


def scrape_one_url(url: str) -> ScrapeOutcome:
    strategy = choose_strategy(url)
    if strategy == "fandom":
        title, html = fetch_fandom_url(url)
        output_path = RAW_HTML_DIR / safe_filename_from_title(title, html)
        output_path.write_text(html, encoding="utf-8")
        return ScrapeOutcome(url=url, strategy="fandom", saved_file=output_path.name, ok=True, message="Saved with wiki shortcut")

    result = fetch_url(url)
    html = result.html
    final_url = result.final_url
    used_strategy = "requests"

    if html_needs_browser(html):
        final_url, html = asyncio.run(fetch_page_html(url))
        used_strategy = "browser"

    title = page_title_from_url(final_url)
    output_path = RAW_HTML_DIR / safe_filename_from_title(title, html)
    output_path.write_text(html, encoding="utf-8")
    return ScrapeOutcome(url=url, strategy=used_strategy, saved_file=output_path.name, ok=True, message="Saved")
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_scrape_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src\page_scraper\scrape_service.py tests\test_scrape_service.py
git commit -m "Add automatic scrape service"
```

## Task 6: Add Background Job State

**Files:**
- Create: `src/page_scraper/job_store.py`
- Test: `tests/test_job_store.py`

- [ ] **Step 1: Write job store tests**

Create `tests/test_job_store.py`:

```python
from page_scraper.job_store import JobStore


def test_job_lifecycle():
    store = JobStore()
    job_id = store.create("scrape")

    store.log(job_id, "Starting")
    store.finish(job_id, {"ok": True})

    job = store.get(job_id)
    assert job["type"] == "scrape"
    assert job["status"] == "done"
    assert job["messages"] == ["Starting"]
    assert job["result"] == {"ok": True}
```

- [ ] **Step 2: Implement job store**

Create `src/page_scraper/job_store.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import time
from uuid import uuid4


@dataclass
class Job:
    id: str
    type: str
    status: str = "running"
    messages: list[str] = field(default_factory=list)
    result: dict | None = None
    error: str | None = None
    created_at: float = field(default_factory=time)


class JobStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, Job] = {}

    def create(self, job_type: str) -> str:
        job_id = uuid4().hex
        with self._lock:
            self._jobs[job_id] = Job(id=job_id, type=job_type)
        return job_id

    def log(self, job_id: str, message: str) -> None:
        with self._lock:
            self._jobs[job_id].messages.append(message)

    def finish(self, job_id: str, result: dict) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "done"
            job.result = result

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "error"
            job.error = error

    def get(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs[job_id]
            return {
                "id": job.id,
                "type": job.type,
                "status": job.status,
                "messages": list(job.messages),
                "result": job.result,
                "error": job.error,
                "created_at": job.created_at,
            }
```

- [ ] **Step 3: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_job_store.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add src\page_scraper\job_store.py tests\test_job_store.py
git commit -m "Add UI job state tracking"
```

## Task 7: Add Local UI Server API

**Files:**
- Create: `src/page_scraper/ui_server.py`
- Modify: `src/page_scraper/paths.py`
- Create: `scripts/launch_ui.py`

- [ ] **Step 1: Add UI path constant**

Modify `src/page_scraper/paths.py`:

```python
UI_DIR = PACKAGE_DIR / "ui"
```

- [ ] **Step 2: Implement server routes**

Create `src/page_scraper/ui_server.py` with these routes:

- `GET /`: serve `src/page_scraper/ui/index.html`
- `GET /styles.css`: serve CSS
- `GET /app.js`: serve JavaScript
- `POST /api/scrape`: accept `{ "urlsText": "..." }`, normalize URLs, start background scrape job, return `{ "jobId": "..." }`
- `POST /api/build/page-records`: run `page_record_parser.main()` in a background job
- `POST /api/build/reference-records`: run `reference_record_parser.main()` in a background job
- `GET /api/jobs/<job_id>`: return job state

Use `ThreadingHTTPServer`, `BaseHTTPRequestHandler`, `json.loads`, and `Thread`.

- [ ] **Step 3: Add launch script**

Create `scripts/launch_ui.py`:

```python
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from page_scraper.ui_server import main


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Smoke check server starts**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\launch_ui.py
```

Expected: terminal prints a local URL such as `http://127.0.0.1:8765` and opens the browser.

- [ ] **Step 5: Commit**

```powershell
git add src\page_scraper\paths.py src\page_scraper\ui_server.py scripts\launch_ui.py
git commit -m "Add local scraper UI server"
```

## Task 8: Build Minimal Browser UI

**Files:**
- Create: `src/page_scraper/ui/index.html`
- Create: `src/page_scraper/ui/styles.css`
- Create: `src/page_scraper/ui/app.js`

- [ ] **Step 1: Create HTML**

Create a single-page layout with:

- Heading: `Page Saver`
- Textarea for pasted links
- Primary button: `Save pages`
- Secondary buttons: `Build page records`, `Build reference records`
- Status region
- Results list
- Collapsible details region

- [ ] **Step 2: Create CSS**

Use a quiet, readable design:

- White or near-white page background
- One centered content column with max width around `860px`
- 8px border radius or less
- High-contrast text
- Large textarea
- Clear primary button
- No decorative gradients or oversized hero treatment

- [ ] **Step 3: Create JavaScript**

Implement:

- submit handler for `Save pages`
- `fetch("/api/scrape", { method: "POST", body: JSON.stringify({ urlsText }) })`
- poll `/api/jobs/<job_id>` every second while job is running
- render user-friendly results
- keep technical strategy names hidden unless `Show details` is opened

- [ ] **Step 4: Browser smoke test**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\launch_ui.py
```

Then in the browser:

1. Paste `https://example.com/`
2. Click `Save pages`
3. Confirm the UI shows progress and then `Saved page files`
4. Confirm a file appears in `data/raw_html/`

- [ ] **Step 5: Commit**

```powershell
git add src\page_scraper\ui\index.html src\page_scraper\ui\styles.css src\page_scraper\ui\app.js
git commit -m "Add simple browser scraper UI"
```

## Task 9: Wire Build Actions Into UI

**Files:**
- Modify: `src/page_scraper/ui_server.py`
- Modify: `src/page_scraper/ui/app.js`

- [ ] **Step 1: Implement build job callbacks**

In `ui_server.py`, import:

```python
from .page_record_parser import main as build_page_records
from .reference_record_parser import main as build_reference_records
```

Make `/api/build/page-records` start a job that calls `build_page_records()`.

Make `/api/build/reference-records` start a job that calls `build_reference_records()`.

- [ ] **Step 2: Add build button behavior**

In `app.js`, wire:

- `Build page records` to `/api/build/page-records`
- `Build reference records` to `/api/build/reference-records`

Use status copy:

- Running: `Building page records...`
- Done: `Page records are ready`
- Running: `Building reference records...`
- Done: `Reference records are ready`

- [ ] **Step 3: Verify parse actions**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\launch_ui.py
```

Click both build buttons.

Expected:

- `data/parsed/page_records/` is cleared and rebuilt by the existing builder.
- `data/parsed/reference_records/` is cleared and rebuilt by the existing builder.
- UI reports success or a plain-language error.

- [ ] **Step 4: Commit**

```powershell
git add src\page_scraper\ui_server.py src\page_scraper\ui\app.js
git commit -m "Add build actions to scraper UI"
```

## Task 10: Document The UI Workflow

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add UI section**

Add:

```markdown
## Browser UI

Launch the local browser UI:

```powershell
.\.venv\Scripts\python.exe scripts\launch_ui.py
```

Use **Save pages** to paste one or more page links and let the app choose the best saving method automatically.

Use **Build page records** after saving pages that contain page-level data.

Use **Build reference records** after saving an index or reference-table page.

Technical notes:

- Final Fantasy Fandom wiki URLs use the existing Fandom API scraper.
- Other URLs use a generalized requests-based scraper first.
- If a page appears to need a browser, the app falls back to Playwright automatically.
- Saved HTML still goes to `data/raw_html/`.
- Generated page JSON goes to `data/parsed/page_records/`.
- Generated reference JSON goes to `data/parsed/reference_records/`.
```

- [ ] **Step 2: Commit**

```powershell
git add README.md
git commit -m "Document browser UI workflow"
```

## Task 11: Full Verification

**Files:**
- No new files.

- [ ] **Step 1: Run unit tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Verify existing parser commands**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\build_page_records.py
.\.venv\Scripts\python.exe scripts\build_reference_records.py
```

Expected: both commands finish successfully and rebuild their output directories.

- [ ] **Step 3: Verify UI happy path**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\launch_ui.py
```

In the browser:

1. Paste `https://example.com/`
2. Click `Save pages`
3. Confirm success copy is non-technical.
4. Open `Show details` and confirm the saved filename and strategy are visible.

- [ ] **Step 4: Verify UI invalid URL path**

In the browser:

1. Paste `not-a-url`
2. Click `Save pages`
3. Confirm the UI says the link could not be used.
4. Confirm no scrape job starts for invalid input only.

- [ ] **Step 5: Final commit**

```powershell
git status --short
git add .
git commit -m "Verify browser scraper UI"
```

## Self-Review

- Spec coverage: The plan covers generalized non-Fandom naming, pasted URLs, a scrape button, automatic scraper selection, generalized requests scraping, preserved Fandom-specific API behavior, minimal browser UI, non-developer UX language, build actions, docs, and verification.
- Placeholder scan: No intentional placeholder tasks remain.
- Type consistency: Strategy names are consistently `fandom`, `requests`, and `browser`; job statuses are consistently `running`, `done`, and `error`.
- Scope check: This is one focused local UI feature. It does not attempt a full desktop app, persistent job history, multi-project scraping configuration, or normalized data browsing.
