# Simple Browser UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a simple local browser UI that lets a non-developer paste page URLs, click one button, and have the project choose the right scraper, save HTML, and optionally rebuild parsed JSON.

**Architecture:** Keep the scraper pipeline in Python. Add a small standard-library local web server that serves one HTML page and JSON endpoints, then add a shared job layer that calls the existing Fandom API, Playwright, monster parser, and feral-link parser code. Do not add a frontend framework; the UI should be plain HTML/CSS/JS because this tool is local, small, and task-focused.

**Tech Stack:** Python 3.12+, `http.server`, `threading`, existing `requests`, existing `playwright`, existing `beautifulsoup4`/`lxml`, plain HTML/CSS/JavaScript.

---

## File Map

- Create `src/ffxiii2_scraper/url_utils.py`: URL cleanup, validation, dedupe, and scraper choice.
- Create `src/ffxiii2_scraper/scrape_job.py`: one high-level job API used by scripts and UI.
- Create `src/ffxiii2_scraper/ui_server.py`: local web server, job registry, browser launch.
- Create `src/ffxiii2_scraper/ui_assets.py`: embedded HTML/CSS/JS strings for the minimal UI.
- Create `scripts/launch_ui.py`: thin entry point that starts the local UI and opens the browser.
- Modify `src/ffxiii2_scraper/fetch_fandom_api.py`: expose reusable `fetch_urls(...)`.
- Modify `src/ffxiii2_scraper/fetch_playwright.py`: expose reusable `fetch_urls(...)`.
- Modify `README.md`: add the friendly UI launch command and describe what the button does.
- Create `tests/test_url_utils.py`: stdlib `unittest` coverage for URL parsing and scraper choice.
- Create `tests/test_scrape_job.py`: focused tests for job planning and parse-option behavior.

## UX Decisions

- Primary label: `Paste page URLs`
- Primary button: `Start scraping`
- Default behavior: `Save pages and rebuild JSON`
- Status language: `Waiting`, `Checking links`, `Saving pages`, `Building JSON files`, `Done`, `Needs attention`
- Avoid dev terms in the UI. Use `Saved pages` instead of `raw HTML`, `JSON files` instead of `parsed output`, and `browser method` only in status details if needed.
- Keep one main screen: URL textbox, start button, progress area, latest results, and a small `More options` disclosure.

## Task 1: URL Cleanup And Scraper Choice

**Files:**
- Create: `src/ffxiii2_scraper/url_utils.py`
- Create: `tests/test_url_utils.py`

- [ ] **Step 1: Write tests for URL cleanup and automatic scraper choice**

```python
import unittest

from ffxiii2_scraper.url_utils import ScraperKind, clean_url_list, choose_scraper


class UrlUtilsTests(unittest.TestCase):
    def test_clean_url_list_dedupes_and_ignores_blank_lines(self):
        urls = clean_url_list("""
        https://finalfantasy.fandom.com/wiki/Chichu

        https://finalfantasy.fandom.com/wiki/Chichu
        https://jegged.com/Games/Final-Fantasy-XIII-2/
        """)

        self.assertEqual(urls, [
            "https://finalfantasy.fandom.com/wiki/Chichu",
            "https://jegged.com/Games/Final-Fantasy-XIII-2/",
        ])

    def test_choose_scraper_uses_fandom_api_for_fandom_wiki_pages(self):
        self.assertEqual(
            choose_scraper("https://finalfantasy.fandom.com/wiki/Chichu"),
            ScraperKind.FANDOM_API,
        )

    def test_choose_scraper_uses_browser_for_other_sites(self):
        self.assertEqual(
            choose_scraper("https://jegged.com/Games/Final-Fantasy-XIII-2/"),
            ScraperKind.BROWSER,
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_url_utils -v
```

Expected: fails because `ffxiii2_scraper.url_utils` does not exist yet.

- [ ] **Step 3: Implement URL utilities**

```python
from enum import StrEnum
from urllib.parse import urlparse


class ScraperKind(StrEnum):
    FANDOM_API = "fandom_api"
    BROWSER = "browser"


def clean_url_list(raw_text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    for line in raw_text.splitlines():
        url = line.strip()
        if not url or url.startswith("#"):
            continue
        if url in seen:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"That does not look like a full web address: {url}")
        seen.add(url)
        urls.append(url)

    return urls


def choose_scraper(url: str) -> ScraperKind:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    if host == "finalfantasy.fandom.com" and path.startswith("/wiki/"):
        return ScraperKind.FANDOM_API

    return ScraperKind.BROWSER
```

- [ ] **Step 4: Run tests and confirm they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_url_utils -v
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src\ffxiii2_scraper\url_utils.py tests\test_url_utils.py
git commit -m "Add URL scraper selection helpers"
```

## Task 2: Reusable Fetch APIs

**Files:**
- Modify: `src/ffxiii2_scraper/fetch_fandom_api.py`
- Modify: `src/ffxiii2_scraper/fetch_playwright.py`

- [ ] **Step 1: Add a progress event type to both modules**

Use this callback shape in both files:

```python
from collections.abc import Callable

ProgressCallback = Callable[[dict], None]
```

- [ ] **Step 2: Refactor Fandom API fetch into `fetch_urls`**

Keep the existing `main()` behavior, but move the loop into:

```python
def fetch_urls(urls: list[str], on_progress: ProgressCallback | None = None) -> list[dict]:
    ensure_project_dirs()
    results: list[dict] = []

    for i, url in enumerate(urls, start=1):
        try:
            title = page_title_from_url(url)
            if on_progress:
                on_progress({"level": "info", "message": f"Saving page {i} of {len(urls)}", "url": url})

            html = fetch_parsed_html(title)
            resolved_title = resolve_disambiguation_title(html)
            if resolved_title and resolved_title != title:
                title = resolved_title
                html = fetch_parsed_html(title)

            output_path = RAW_HTML_DIR / safe_filename_from_title(title, html)
            output_path.write_text(html, encoding="utf-8")
            result = {"ok": True, "url": url, "file": output_path.name, "method": "Fandom API"}
            results.append(result)
            if on_progress:
                on_progress({"level": "success", "message": f"Saved {output_path.name}", "url": url})
            time.sleep(REQUEST_DELAY_SECONDS)
        except Exception as exc:
            result = {"ok": False, "url": url, "error": str(exc), "method": "Fandom API"}
            results.append(result)
            if on_progress:
                on_progress({"level": "error", "message": str(exc), "url": url})

    return results
```

Then update `main()` to load `MONSTER_URLS_FILE`, print progress, call `fetch_urls(urls)`, and print `Done.`

- [ ] **Step 3: Refactor Playwright fetch into async `fetch_urls`**

Use the same result dictionary shape:

```python
async def fetch_urls(urls: list[str], on_progress: ProgressCallback | None = None) -> list[dict]:
    ensure_project_dirs()
    results: list[dict] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ))
        page = await context.new_page()

        for i, url in enumerate(urls, start=1):
            try:
                if on_progress:
                    on_progress({"level": "info", "message": f"Saving page {i} of {len(urls)}", "url": url})
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(2000)
                html = await page.content()
                title = page_title_from_url(page.url or url)
                output_path = RAW_HTML_DIR / safe_filename_from_title(title, html)
                output_path.write_text(html, encoding="utf-8")
                result = {"ok": True, "url": url, "file": output_path.name, "method": "Browser"}
                results.append(result)
                if on_progress:
                    on_progress({"level": "success", "message": f"Saved {output_path.name}", "url": url})
                await asyncio.sleep(REQUEST_DELAY_SECONDS)
            except Exception as exc:
                result = {"ok": False, "url": url, "error": str(exc), "method": "Browser"}
                results.append(result)
                if on_progress:
                    on_progress({"level": "error", "message": str(exc), "url": url})

        await browser.close()

    return results
```

- [ ] **Step 4: Run existing commands**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\scrape_fandom_api.py
.\.venv\Scripts\python.exe scripts\scrape_playwright.py
```

Expected: both scripts still load `inputs/monster_urls.txt`, save files under `data/raw_html/`, and print `Done.`

- [ ] **Step 5: Commit**

```powershell
git add src\ffxiii2_scraper\fetch_fandom_api.py src\ffxiii2_scraper\fetch_playwright.py
git commit -m "Expose reusable fetch functions"
```

## Task 3: High-Level Scrape Job

**Files:**
- Create: `src/ffxiii2_scraper/scrape_job.py`
- Create: `tests/test_scrape_job.py`

- [ ] **Step 1: Write tests for job planning**

```python
import unittest

from ffxiii2_scraper.scrape_job import build_scrape_plan
from ffxiii2_scraper.url_utils import ScraperKind


class ScrapeJobTests(unittest.TestCase):
    def test_build_scrape_plan_groups_urls_by_scraper(self):
        plan = build_scrape_plan([
            "https://finalfantasy.fandom.com/wiki/Chichu",
            "https://jegged.com/Games/Final-Fantasy-XIII-2/",
        ])

        self.assertEqual(plan[ScraperKind.FANDOM_API], ["https://finalfantasy.fandom.com/wiki/Chichu"])
        self.assertEqual(plan[ScraperKind.BROWSER], ["https://jegged.com/Games/Final-Fantasy-XIII-2/"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_scrape_job -v
```

Expected: fails because `scrape_job.py` does not exist yet.

- [ ] **Step 3: Implement `scrape_job.py`**

```python
import asyncio
from collections.abc import Callable

from . import fetch_fandom_api, fetch_playwright, feral_link_parser, monster_parser
from .url_utils import ScraperKind, choose_scraper


ProgressCallback = Callable[[dict], None]


def build_scrape_plan(urls: list[str]) -> dict[ScraperKind, list[str]]:
    plan = {
        ScraperKind.FANDOM_API: [],
        ScraperKind.BROWSER: [],
    }
    for url in urls:
        plan[choose_scraper(url)].append(url)
    return plan


def run_scrape_job(
    urls: list[str],
    rebuild_json: bool = True,
    on_progress: ProgressCallback | None = None,
) -> dict:
    plan = build_scrape_plan(urls)
    results: list[dict] = []

    if on_progress:
        on_progress({"level": "info", "message": "Checking links"})

    if plan[ScraperKind.FANDOM_API]:
        results.extend(fetch_fandom_api.fetch_urls(plan[ScraperKind.FANDOM_API], on_progress=on_progress))

    if plan[ScraperKind.BROWSER]:
        results.extend(asyncio.run(fetch_playwright.fetch_urls(plan[ScraperKind.BROWSER], on_progress=on_progress)))

    if rebuild_json:
        if on_progress:
            on_progress({"level": "info", "message": "Building monster JSON files"})
        monster_parser.main()
        if on_progress:
            on_progress({"level": "info", "message": "Building Feral Link JSON files"})
        feral_link_parser.main()

    ok_count = sum(1 for result in results if result.get("ok"))
    failed_count = len(results) - ok_count
    return {
        "ok": failed_count == 0,
        "saved": ok_count,
        "failed": failed_count,
        "results": results,
    }
```

- [ ] **Step 4: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_url_utils tests.test_scrape_job -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src\ffxiii2_scraper\scrape_job.py tests\test_scrape_job.py
git commit -m "Add high level scrape job"
```

## Task 4: Local UI Server

**Files:**
- Create: `src/ffxiii2_scraper/ui_assets.py`
- Create: `src/ffxiii2_scraper/ui_server.py`
- Create: `scripts/launch_ui.py`

- [ ] **Step 1: Create the UI assets**

Put the page markup, CSS, and JavaScript in `ui_assets.py`. The interface should include:

```python
INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FFXIII-2 Scraper</title>
  <link rel="stylesheet" href="/assets/app.css">
</head>
<body>
  <main class="shell">
    <section class="panel">
      <p class="eyebrow">FFXIII-2 data tool</p>
      <h1>Save wiki pages and build JSON</h1>
      <label for="urls">Paste page URLs</label>
      <textarea id="urls" rows="9" placeholder="https://finalfantasy.fandom.com/wiki/Chichu"></textarea>
      <details>
        <summary>More options</summary>
        <label class="check"><input id="rebuildJson" type="checkbox" checked> Build JSON files after saving pages</label>
      </details>
      <button id="startButton" type="button">Start scraping</button>
      <p id="status" role="status">Waiting for links.</p>
    </section>
    <section class="results" aria-live="polite">
      <h2>Progress</h2>
      <ol id="events"></ol>
    </section>
  </main>
  <script src="/assets/app.js"></script>
</body>
</html>
"""
```

CSS requirements:

- White/off-white background.
- One centered content column.
- Large textarea.
- One high-contrast primary button.
- Clear success/error event rows.
- Mobile width support down to 360px.

JavaScript requirements:

- Read `#urls` and `#rebuildJson`.
- POST `/api/jobs`.
- Poll `/api/jobs/{job_id}` every 800ms until status is `done` or `error`.
- Disable the button while a job runs.
- Show plain-language messages from the server.

- [ ] **Step 2: Implement `ui_server.py`**

Use `ThreadingHTTPServer` and an in-memory job dictionary:

```python
from __future__ import annotations

import json
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .scrape_job import run_scrape_job
from .ui_assets import APP_CSS, APP_JS, INDEX_HTML
from .url_utils import clean_url_list


JOBS: dict[str, dict] = {}


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _text_response(handler: BaseHTTPRequestHandler, status: int, body: str, content_type: str) -> None:
    data = body.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class ScraperUiHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            _text_response(self, 200, INDEX_HTML, "text/html; charset=utf-8")
            return
        if path == "/assets/app.css":
            _text_response(self, 200, APP_CSS, "text/css; charset=utf-8")
            return
        if path == "/assets/app.js":
            _text_response(self, 200, APP_JS, "text/javascript; charset=utf-8")
            return
        if path.startswith("/api/jobs/"):
            job_id = path.removeprefix("/api/jobs/")
            job = JOBS.get(job_id)
            if job is None:
                _json_response(self, 404, {"error": "Job not found"})
                return
            _json_response(self, 200, job)
            return
        _json_response(self, 404, {"error": "Not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/jobs":
            _json_response(self, 404, {"error": "Not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        try:
            urls = clean_url_list(payload.get("urls", ""))
        except ValueError as exc:
            _json_response(self, 400, {"error": str(exc)})
            return
        if not urls:
            _json_response(self, 400, {"error": "Paste at least one full page URL."})
            return

        job_id = uuid.uuid4().hex
        JOBS[job_id] = {"id": job_id, "status": "running", "events": [{"level": "info", "message": "Starting"}], "result": None}
        thread = threading.Thread(
            target=_run_job,
            args=(job_id, urls, bool(payload.get("rebuild_json", True))),
            daemon=True,
        )
        thread.start()
        _json_response(self, 202, {"job_id": job_id})


def _run_job(job_id: str, urls: list[str], rebuild_json: bool) -> None:
    def on_progress(event: dict) -> None:
        JOBS[job_id]["events"].append(event)

    try:
        result = run_scrape_job(urls, rebuild_json=rebuild_json, on_progress=on_progress)
        JOBS[job_id]["status"] = "done" if result["ok"] else "error"
        JOBS[job_id]["result"] = result
        JOBS[job_id]["events"].append({"level": "success" if result["ok"] else "error", "message": "Done" if result["ok"] else "Finished with issues"})
    except Exception as exc:
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["events"].append({"level": "error", "message": str(exc)})


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    server = ThreadingHTTPServer((host, port), ScraperUiHandler)
    url = f"http://{host}:{port}/"
    if open_browser:
        webbrowser.open(url)
    print(f"Scraper UI is running at {url}")
    server.serve_forever()
```

- [ ] **Step 3: Add launch script**

```python
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ffxiii2_scraper.ui_server import serve


if __name__ == "__main__":
    serve()
```

- [ ] **Step 4: Start the UI**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\launch_ui.py
```

Expected: terminal prints `Scraper UI is running at http://127.0.0.1:8765/` and the browser opens.

- [ ] **Step 5: Commit**

```powershell
git add src\ffxiii2_scraper\ui_assets.py src\ffxiii2_scraper\ui_server.py scripts\launch_ui.py
git commit -m "Add local scraper browser UI"
```

## Task 5: Friendly Workflow Polish

**Files:**
- Modify: `src/ffxiii2_scraper/ui_assets.py`
- Modify: `README.md`

- [ ] **Step 1: Make the UI text non-technical**

Use these strings:

- `Paste one page per line. Fandom wiki pages use the faster save method automatically; other sites use the browser method.`
- `Build JSON files after saving pages`
- `Saved pages`
- `Finished with issues`
- `Open the folders in this project to see saved pages and JSON files.`

- [ ] **Step 2: Add README instructions**

Add:

```markdown
## Browser UI

Launch the local UI:

```powershell
.\.venv\Scripts\python.exe scripts\launch_ui.py
```

Paste one page URL per line and click **Start scraping**. The tool chooses the fast Fandom API scraper for Final Fantasy Fandom wiki pages and the browser scraper for other sites. By default, it rebuilds the monster and Feral Link JSON files after saving pages.
```

- [ ] **Step 3: Manual smoke test**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\launch_ui.py
```

Then paste:

```text
https://finalfantasy.fandom.com/wiki/Chichu
```

Expected:

- UI shows `Starting`, then saving progress, then JSON-building progress.
- A saved page appears in `data/raw_html/`.
- Monster JSON rebuild completes under `data/parsed/monsters/`.

- [ ] **Step 4: Commit**

```powershell
git add README.md src\ffxiii2_scraper\ui_assets.py
git commit -m "Document browser UI workflow"
```

## Final Verification

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\parse_monsters.py
.\.venv\Scripts\python.exe scripts\parse_feral_links.py
.\.venv\Scripts\python.exe scripts\launch_ui.py
```

Expected:

- Unit tests pass.
- Monster parser clears and rebuilds `data/parsed/monsters/`.
- Feral Link parser clears and rebuilds `data/parsed/feral_links/`.
- UI opens at `http://127.0.0.1:8765/`.
- Scraping one Fandom URL saves a page and displays friendly progress.

## Implementation Notes

- Keep `scripts/` as thin wrappers.
- Do not hand-edit generated JSON.
- Keep scraper selection automatic; expose details only as progress messages.
- Keep the first UI version local-only. No accounts, no database, no packaging, no external web server.
- If port `8765` is busy, add a small helper that tries `8766`, `8767`, and `8768` before failing with a plain message.
