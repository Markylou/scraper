# Local API Spec Without DB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define and implement a stable local JSON API that a richer local frontend can call for saving pages, discovering pages/files, selecting downloads, monitoring jobs, and reading manifests, without adding SQLite or any other database.

**Architecture:** Keep the current `ThreadingHTTPServer` entry point in `src/page_scraper/ui_server.py` and the in-memory `JobStore` as the live runtime state. Add a small API contract layer around the current backend models so response shapes, errors, status names, and frontend polling behavior are predictable. Persist completed output only through the existing filesystem job folders under `data/jobs/<site>_<job-id>/` and `manifest.json`.

**Tech Stack:** Python 3.12, standard-library HTTP server, in-memory job store, filesystem job output, JSON over localhost HTTP, existing manual/pytest-style tests.

---

## Current Source Of Truth

The API work originally came from `docs/superpowers/plans/2026-05-05-local-backend-engine-no-sqlite.md`, especially Task 10. That file is now historical because it still mentions preserving `data/pages/`; the current architecture puts normal saved output under `data/jobs/`.

Current docs that should stay aligned with this plan:

- `AGENTS.md`
- `README.md`
- `docs/pipeline_notes.md`
- `Documentation.md`

Current implementation entry points:

- `src/page_scraper/ui_server.py`: local HTTP routes and background job launch.
- `src/page_scraper/job_store.py`: in-memory job, page, asset, event, and failure state.
- `src/page_scraper/core/crawler.py`: page discovery.
- `src/page_scraper/core/downloader.py`: selected page/file download.
- `src/page_scraper/core/manifest.py`: `manifest.json` writer.
- `src/page_scraper/scrape_service.py`: explicit pasted URL save flow.

## API Design Decisions

- No DB in this phase.
- No FastAPI, Vue, Electron, WebSockets, auth, cloud hosting, or packaging in this phase.
- Keep localhost-only HTTP and JSON so any frontend can call it.
- Keep current routes working for the existing simple UI.
- Add stable response envelopes and docs so a future Vue app does not depend on incidental `JobStore` internals.
- Use polling first. Add optional incremental event polling with `afterEventId`; save Server-Sent Events for later if polling becomes painful.
- Prefer user-facing terms in frontend text, but use precise backend names in JSON.

## Target API Shape

### Standard JSON Envelope

Successful responses should use one of these shapes:

```json
{
  "ok": true,
  "data": {}
}
```

```json
{
  "ok": true,
  "data": [],
  "meta": {
    "count": 0
  }
}
```

Errors should use this shape:

```json
{
  "ok": false,
  "error": {
    "code": "invalid_request",
    "message": "Enter a starting page link.",
    "details": {}
  }
}
```

Keep compatibility aliases during the transition where the current UI expects them, such as `jobId`, `job`, `pages`, `assets`, `events`, and `failures`.

### Stable Models

#### Job

```json
{
  "id": "abc123",
  "type": "crawl",
  "status": "ready",
  "sourceUrl": "https://jegged.com/Games/Final-Fantasy-X/",
  "normalizedSourceUrl": "https://jegged.com/Games/Final-Fantasy-X/",
  "settings": {
    "maxDepth": 2,
    "sameDomainOnly": true,
    "stayUnderStartPath": true,
    "includeImages": true,
    "includeDocuments": true,
    "includeVideo": false
  },
  "summary": {
    "pagesFound": 0,
    "pagesSelected": 0,
    "assetsFound": 0,
    "assetsSelected": 0,
    "failures": 0
  },
  "output": {
    "root": "data/jobs/jegged_abc12345",
    "manifest": "data/jobs/jegged_abc12345/manifest.json"
  },
  "createdAt": "2026-05-05T00:00:00+00:00",
  "updatedAt": "2026-05-05T00:00:00+00:00",
  "paused": false,
  "cancelled": false
}
```

#### Page

```json
{
  "id": "https://jegged.com/Games/Final-Fantasy-X/",
  "jobId": "abc123",
  "url": "https://jegged.com/Games/Final-Fantasy-X/",
  "normalizedUrl": "https://jegged.com/Games/Final-Fantasy-X/",
  "title": "Final Fantasy X",
  "depth": 0,
  "selected": true,
  "status": "discovered",
  "localPath": null,
  "httpStatus": null,
  "contentType": null,
  "sizeBytes": null,
  "discoveredFromUrl": null,
  "errorMessage": null,
  "createdAt": "2026-05-05T00:00:00+00:00",
  "updatedAt": "2026-05-05T00:00:00+00:00"
}
```

#### Asset

```json
{
  "id": "https://jegged.com/img/Games/Final-Fantasy-X/Monster-Arena/Achelous.webp",
  "jobId": "abc123",
  "pageId": "https://jegged.com/Games/Final-Fantasy-X/",
  "url": "https://jegged.com/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-540w.webp",
  "normalizedUrl": "https://jegged.com/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-540w.webp",
  "assetType": "image",
  "selected": true,
  "status": "discovered",
  "localPath": null,
  "httpStatus": null,
  "contentType": null,
  "sizeBytes": null,
  "discoveredFromUrl": "https://jegged.com/Games/Final-Fantasy-X/",
  "errorMessage": null,
  "variantGroupId": "https://jegged.com/img/Games/Final-Fantasy-X/Monster-Arena/Achelous.webp",
  "variants": [
    {
      "url": "https://jegged.com/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-100w.webp",
      "label": "100w",
      "width": 100,
      "occurrenceCount": 2
    }
  ],
  "variantCount": 3,
  "occurrenceCount": 6,
  "selectedVariantUrl": "https://jegged.com/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-540w.webp",
  "createdAt": "2026-05-05T00:00:00+00:00",
  "updatedAt": "2026-05-05T00:00:00+00:00"
}
```

#### Event

```json
{
  "id": 1,
  "jobId": "abc123",
  "level": "info",
  "eventType": "page_discovered",
  "message": "Found a page",
  "metadata": {
    "url": "https://jegged.com/Games/Final-Fantasy-X/"
  },
  "createdAt": "2026-05-05T00:00:00+00:00"
}
```

#### Failure

```json
{
  "id": "failure-id",
  "jobId": "abc123",
  "relatedType": "page",
  "relatedId": "https://jegged.com/Games/Final-Fantasy-X/",
  "url": "https://jegged.com/Games/Final-Fantasy-X/",
  "failureCode": "fetch_failed",
  "message": "Could not download this page.",
  "details": {},
  "createdAt": "2026-05-05T00:00:00+00:00"
}
```

### Job Statuses

Use these stable API statuses:

- `created`
- `discovering`
- `ready`
- `downloading`
- `paused`
- `completed`
- `completed_with_errors`
- `failed`
- `cancelled`

Keep translating old internal/UI statuses where needed:

- `done` should map to `completed` or `ready` based on job type and result.
- `error` should map to `failed`.
- `running` should map to `downloading` for save jobs and to `discovering` for discovery jobs when possible.

### Routes

#### General

- `GET /api/health`
  - Returns server health, API version, and capabilities.

- `POST /api/system/open-folder`
  - Opens a folder under `data/jobs/` on Windows.
  - Rejects paths outside `data/jobs/`.

#### Explicit Save Pages Flow

- `POST /api/scrape`
  - Compatibility route for the existing UI.
  - Body: `{ "urlsText": "https://example.com/a\nhttps://example.com/b" }`
  - Starts a save job under `data/jobs/<site>_<job-id>/`.

- `POST /api/jobs/save`
  - New stable route for future frontend use.
  - Body: `{ "urls": ["https://example.com/a"], "urlsText": "" }`
  - Returns the same job model as crawler jobs.

- `POST /api/jobs/{job_id}/pages/add`
  - Adds one or more page URLs to an existing job as selected pages.
  - Body: `{ "urls": ["https://example.com/a"], "urlsText": "https://example.com/b" }`
  - Intended for the future `+ Add URL` UI affordance.

#### Crawler Flow

- `POST /api/jobs`
  - Creates a crawl job.
  - Body: `sourceUrl`, `maxDepth`, `sameDomainOnly`, `stayUnderStartPath`, `includeImages`, `includeDocuments`, `includeVideo`.

- `POST /api/jobs/{job_id}/discover`
  - Starts discovery for an existing crawl job.

- `GET /api/jobs/{job_id}`
  - Returns normalized job summary.

- `GET /api/jobs/{job_id}/pages`
  - Returns discovered pages.

- `PATCH /api/jobs/{job_id}/pages/selection`
  - Body: `{ "ids": ["page-id"], "selected": false }`

- `GET /api/jobs/{job_id}/assets`
  - Returns discovered assets and image variant groups.

- `PATCH /api/jobs/{job_id}/assets/selection`
  - Body: `{ "ids": ["asset-id"], "selected": false }`

- `PATCH /api/jobs/{job_id}/assets/variant`
  - Body: `{ "assetId": "asset-id", "url": "https://example.com/image-540w.webp" }`

- `POST /api/jobs/{job_id}/download`
  - Downloads selected pages and selected assets.

- `POST /api/jobs/{job_id}/pause`
  - Requests pause at the next safe queue boundary.

- `POST /api/jobs/{job_id}/resume`
  - Clears pause and resumes queued work.

- `POST /api/jobs/{job_id}/cancel`
  - Cancels queued work and marks the job cancelled.

- `POST /api/jobs/{job_id}/failures/{failure_id}/retry`
  - Re-queues the page or file connected to a recorded failure.
  - Starts the existing downloader in the background.
  - Retries only failures tied to known page or asset records in v1.

#### Monitoring And Output

- `GET /api/jobs/{job_id}/events`
  - Returns events.
  - Optional query: `?afterEventId=12`

- `GET /api/jobs/{job_id}/failures`
  - Returns structured failures.

- `GET /api/jobs/{job_id}/manifest`
  - Writes or refreshes `manifest.json` and returns its path and parsed contents.

#### Derived Content Refresh

- `POST /api/build/page-content`
  - Compatibility route for rebuilding `content.html`, `content.md`, and `metadata.json` from existing `source.html`.

## File Structure

- Modify: `src/page_scraper/ui_server.py`
  - Keep route registration in the existing simple HTTP server.
  - Add response helpers, error handling, query parsing, and stable envelope output.

- Create: `src/page_scraper/api_contract.py`
  - Convert internal snake_case `JobStore` dictionaries into stable frontend-facing camelCase JSON models.
  - Centralize status mapping and summary counts.
  - Centralize standard success/error envelopes.

- Modify: `src/page_scraper/job_store.py`
  - Add `updated_at` on jobs if missing.
  - Preserve existing snake_case internals.
  - Avoid DB-style repositories or persistence.

- Create: `tests/test_api_contract.py`
  - Unit-test model normalization without launching the HTTP server.

- Create: `tests/test_ui_api.py`
  - Exercise local HTTP handler behavior with a test server or direct handler helpers.

- Modify: `README.md`
  - Add a short “Local API” section for frontend developers.

- Modify: `docs/pipeline_notes.md`
  - Link the API lifecycle to the current `data/jobs/` output model.

- Modify: `Documentation.md`
  - Add dated progress notes as tasks are implemented.

---

### Task 1: Document Current API Baseline

**Files:**
- Modify: `Documentation.md`
- Create: `docs/api.md`

- [ ] **Step 1: Create the initial API docs file**

Add `docs/api.md` with this starting content:

```markdown
# Local Page Scraper API

The local API is served by `scripts/launch_ui.py` at `http://127.0.0.1:8765` by default.

This API is intended for local frontends. It does not use a database. Active jobs live in memory while the server is running. Downloaded output is written to `data/jobs/<site>_<job-id>/`, and completed job summaries are represented by `manifest.json`.

## Current Compatibility Routes

- `POST /api/scrape`
- `POST /api/jobs/save`
- `POST /api/build/page-content`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/pages`
- `GET /api/jobs/{job_id}/assets`
- `GET /api/jobs/{job_id}/events`
- `GET /api/jobs/{job_id}/failures`
- `GET /api/jobs/{job_id}/manifest`
- `POST /api/jobs`
- `POST /api/jobs/{job_id}/pages/add`
- `POST /api/jobs/{job_id}/discover`
- `POST /api/jobs/{job_id}/download`
- `POST /api/jobs/{job_id}/pause`
- `POST /api/jobs/{job_id}/resume`
- `POST /api/jobs/{job_id}/cancel`
- `POST /api/jobs/{job_id}/failures/{failure_id}/retry`
- `POST /api/system/open-folder`
- `PATCH /api/jobs/{job_id}/pages/selection`
- `PATCH /api/jobs/{job_id}/assets/selection`
- `PATCH /api/jobs/{job_id}/assets/variant`
```

- [ ] **Step 2: Add a progress note**

Append this to `Documentation.md`:

```markdown
## 2026-05-05 Local API Spec Planning

- Started a dedicated local API spec for frontend use.
- Confirmed the current implementation lives in `src/page_scraper/ui_server.py` and uses in-memory jobs from `src/page_scraper/job_store.py`.
- Kept SQLite, durable job history, FastAPI, WebSockets, and frontend framework migration out of scope for this phase.
```

- [ ] **Step 3: Verify docs mention no DB**

Run:

```powershell
Select-String -Path docs\api.md,Documentation.md -Pattern "database|SQLite|data/jobs|ui_server"
```

Expected: output includes `does not use a database`, `data/jobs`, and `ui_server.py`.

### Task 2: Add API Contract Helpers

**Files:**
- Create: `src/page_scraper/api_contract.py`
- Create: `tests/test_api_contract.py`

- [ ] **Step 1: Write failing tests for envelopes and status mapping**

Create `tests/test_api_contract.py`:

```python
from page_scraper.api_contract import error_response, map_job_status, success_response


def test_success_response_wraps_data():
    assert success_response({"id": "job-1"}) == {"ok": True, "data": {"id": "job-1"}}


def test_error_response_wraps_error_details():
    assert error_response("invalid_request", "Bad input", {"field": "sourceUrl"}) == {
        "ok": False,
        "error": {
            "code": "invalid_request",
            "message": "Bad input",
            "details": {"field": "sourceUrl"},
        },
    }


def test_map_job_status_translates_legacy_statuses():
    assert map_job_status("done", job_type="scrape") == "completed"
    assert map_job_status("error", job_type="crawl") == "failed"
    assert map_job_status("running", job_type="crawl") == "discovering"
    assert map_job_status("running", job_type="scrape") == "downloading"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_contract.py -v
```

Expected: FAIL because `page_scraper.api_contract` does not exist.

- [ ] **Step 3: Implement the contract helpers**

Create `src/page_scraper/api_contract.py`:

```python
from __future__ import annotations

from typing import Any


def success_response(data: Any, meta: dict | None = None) -> dict:
    payload = {"ok": True, "data": data}
    if meta is not None:
        payload["meta"] = meta
    return payload


def error_response(code: str, message: str, details: dict | None = None) -> dict:
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }


def map_job_status(status: str, job_type: str | None = None) -> str:
    if status == "done":
        return "completed"
    if status == "error":
        return "failed"
    if status == "running" and job_type == "crawl":
        return "discovering"
    if status == "running" and job_type == "scrape":
        return "downloading"
    return status
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_contract.py -v
```

Expected: PASS.

### Task 3: Normalize Job/Page/Asset/Event/Failure Models

**Files:**
- Modify: `src/page_scraper/api_contract.py`
- Modify: `tests/test_api_contract.py`

- [ ] **Step 1: Add tests for frontend-facing model keys**

Append to `tests/test_api_contract.py`:

```python
from page_scraper.api_contract import api_asset, api_event, api_failure, api_job, api_page


def test_api_job_uses_camel_case_and_summary_counts():
    job = api_job(
        {
            "id": "job-1",
            "type": "crawl",
            "status": "ready",
            "source_url": "https://example.com/start",
            "normalized_source_url": "https://example.com/start",
            "settings": {"max_depth": 2},
            "output_root": "data/jobs/example_job1",
            "created_at": 1.0,
            "events": [],
            "failures": [{}],
            "pages": [{"selected": True}, {"selected": False}],
            "assets": [{"selected": True}],
            "paused": False,
            "cancelled": False,
        }
    )
    assert job["sourceUrl"] == "https://example.com/start"
    assert job["normalizedSourceUrl"] == "https://example.com/start"
    assert job["summary"] == {
        "pagesFound": 2,
        "pagesSelected": 1,
        "assetsFound": 1,
        "assetsSelected": 1,
        "failures": 1,
    }
    assert job["output"]["root"] == "data/jobs/example_job1"


def test_api_page_uses_camel_case():
    page = api_page(
        {
            "id": "p1",
            "job_id": "job-1",
            "normalized_url": "https://example.com/a",
            "http_status": 200,
            "content_type": "text/html",
            "size_bytes": 10,
            "local_path": "pages/a/source.html",
            "discovered_from_url": None,
            "error_message": None,
        }
    )
    assert page["jobId"] == "job-1"
    assert page["normalizedUrl"] == "https://example.com/a"
    assert page["httpStatus"] == 200
    assert page["sizeBytes"] == 10


def test_api_asset_preserves_variant_data():
    asset = api_asset(
        {
            "id": "a1",
            "job_id": "job-1",
            "page_id": "p1",
            "asset_type": "image",
            "normalized_url": "https://example.com/i-540w.webp",
            "variant_group_id": "https://example.com/i.webp",
            "variant_count": 2,
            "occurrence_count": 4,
            "selected_variant_url": "https://example.com/i-540w.webp",
            "variants": [],
        }
    )
    assert asset["jobId"] == "job-1"
    assert asset["pageId"] == "p1"
    assert asset["assetType"] == "image"
    assert asset["variantGroupId"] == "https://example.com/i.webp"
    assert asset["variantCount"] == 2


def test_api_event_and_failure_use_camel_case():
    event = api_event({"job_id": "job-1", "event_type": "job_created", "created_at": "now"})
    failure = api_failure({"job_id": "job-1", "related_type": "page", "failure_code": "fetch_failed", "created_at": "now"})
    assert event["jobId"] == "job-1"
    assert event["eventType"] == "job_created"
    assert failure["relatedType"] == "page"
    assert failure["failureCode"] == "fetch_failed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_contract.py -v
```

Expected: FAIL because model conversion helpers do not exist.

- [ ] **Step 3: Implement model conversion helpers**

Extend `src/page_scraper/api_contract.py`:

```python
def _get(record: dict, key: str, default: Any = None) -> Any:
    return record.get(key, default)


def api_job(job: dict) -> dict:
    pages = list(job.get("pages", []))
    assets = list(job.get("assets", []))
    failures = list(job.get("failures", []))
    output_root = job.get("output_root")
    return {
        "id": job.get("id"),
        "type": job.get("type"),
        "status": map_job_status(str(job.get("status")), job_type=job.get("type")),
        "sourceUrl": job.get("source_url"),
        "normalizedSourceUrl": job.get("normalized_source_url"),
        "settings": job.get("settings", {}),
        "summary": {
            "pagesFound": len(pages),
            "pagesSelected": len([page for page in pages if page.get("selected")]),
            "assetsFound": len(assets),
            "assetsSelected": len([asset for asset in assets if asset.get("selected")]),
            "failures": len(failures),
        },
        "output": {
            "root": output_root,
            "manifest": f"{output_root}/manifest.json" if output_root else None,
        },
        "createdAt": job.get("created_at"),
        "updatedAt": job.get("updated_at"),
        "paused": bool(job.get("paused", False)),
        "cancelled": bool(job.get("cancelled", False)),
        "messages": job.get("messages", []),
        "error": job.get("error"),
        "result": job.get("result"),
    }


def api_page(page: dict) -> dict:
    return {
        "id": page.get("id"),
        "jobId": page.get("job_id"),
        "url": page.get("url"),
        "normalizedUrl": page.get("normalized_url"),
        "title": page.get("title"),
        "depth": page.get("depth"),
        "selected": page.get("selected"),
        "status": page.get("status"),
        "localPath": page.get("local_path"),
        "httpStatus": page.get("http_status"),
        "contentType": page.get("content_type"),
        "sizeBytes": page.get("size_bytes"),
        "discoveredFromUrl": page.get("discovered_from_url"),
        "errorMessage": page.get("error_message"),
        "createdAt": page.get("created_at"),
        "updatedAt": page.get("updated_at"),
    }


def api_asset(asset: dict) -> dict:
    return {
        "id": asset.get("id"),
        "jobId": asset.get("job_id"),
        "pageId": asset.get("page_id"),
        "url": asset.get("url"),
        "normalizedUrl": asset.get("normalized_url"),
        "assetType": asset.get("asset_type"),
        "selected": asset.get("selected"),
        "status": asset.get("status"),
        "localPath": asset.get("local_path"),
        "httpStatus": asset.get("http_status"),
        "contentType": asset.get("content_type"),
        "sizeBytes": asset.get("size_bytes"),
        "discoveredFromUrl": asset.get("discovered_from_url"),
        "errorMessage": asset.get("error_message"),
        "variantGroupId": asset.get("variant_group_id"),
        "variants": asset.get("variants", []),
        "variantCount": asset.get("variant_count", 1),
        "occurrenceCount": asset.get("occurrence_count", 1),
        "selectedVariantUrl": asset.get("selected_variant_url"),
        "createdAt": asset.get("created_at"),
        "updatedAt": asset.get("updated_at"),
    }


def api_event(event: dict) -> dict:
    return {
        "id": event.get("id"),
        "jobId": event.get("job_id"),
        "level": event.get("level"),
        "eventType": event.get("event_type"),
        "message": event.get("message"),
        "metadata": event.get("metadata", {}),
        "createdAt": event.get("created_at"),
    }


def api_failure(failure: dict) -> dict:
    return {
        "id": failure.get("id"),
        "jobId": failure.get("job_id"),
        "relatedType": failure.get("related_type"),
        "relatedId": failure.get("related_id"),
        "url": failure.get("url"),
        "failureCode": failure.get("failure_code"),
        "message": failure.get("message"),
        "details": failure.get("details", {}),
        "createdAt": failure.get("created_at"),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_contract.py -v
```

Expected: PASS.

### Task 4: Add Stable API Responses While Preserving Compatibility

**Files:**
- Modify: `src/page_scraper/ui_server.py`
- Create: `tests/test_ui_api.py`

- [ ] **Step 1: Write tests for health and bad request envelopes**

Create `tests/test_ui_api.py` with helper-level tests first:

```python
from page_scraper.api_contract import error_response, success_response


def test_health_contract_shape():
    response = success_response(
        {
            "server": "PageScraperUI/0.1",
            "apiVersion": "1",
            "capabilities": ["save-pages", "discover-pages"],
        }
    )
    assert response["ok"] is True
    assert response["data"]["apiVersion"] == "1"


def test_bad_request_contract_shape():
    response = error_response("invalid_request", "Enter a starting page link.")
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_request"
```

- [ ] **Step 2: Run tests to verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ui_api.py -v
```

Expected: PASS.

- [ ] **Step 3: Import contract helpers in the server**

Modify `src/page_scraper/ui_server.py` imports:

```python
from .api_contract import (
    api_asset,
    api_event,
    api_failure,
    api_job,
    api_page,
    error_response,
    success_response,
)
```

- [ ] **Step 4: Add helper methods to the handler**

Add these methods inside `UIServerHandler`:

```python
    def send_api_data(self, data: Any, status: HTTPStatus = HTTPStatus.OK, meta: dict | None = None, **compat) -> None:
        payload = success_response(data, meta=meta)
        payload.update(compat)
        self.send_json(payload, status=status)

    def send_api_error(
        self,
        code: str,
        message: str,
        status: HTTPStatus = HTTPStatus.BAD_REQUEST,
        details: dict | None = None,
        **compat,
    ) -> None:
        payload = error_response(code, message, details)
        payload.update(compat)
        self.send_json(payload, status=status)
```

- [ ] **Step 5: Update `GET /api/health`**

Change the health response to:

```python
self.send_api_data(
    {
        "server": self.server_version,
        "apiVersion": "1",
        "capabilities": [
            "save-pages",
            "refresh-content",
            "discover-pages",
            "download-selected",
            "image-variant-selection",
        ],
    }
)
```

- [ ] **Step 6: Keep compatibility keys on existing route responses**

For list routes, return both stable and compatibility keys:

```python
pages = [api_page(page) for page in JOBS.pages(job_id)]
self.send_api_data(pages, meta={"count": len(pages)}, pages=pages)
```

Use the same pattern for assets, events, and failures.

- [ ] **Step 7: Run focused tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_contract.py tests\test_ui_api.py -v
```

Expected: PASS.

### Task 5: Add Stable Save Job Route

**Files:**
- Modify: `src/page_scraper/ui_server.py`
- Modify: `docs/api.md`
- Modify: `tests/test_ui_api.py`

- [ ] **Step 1: Document the new route**

Append to `docs/api.md`:

````markdown
## Save Pages

### `POST /api/jobs/save`

Starts a job that saves explicit page URLs.

Request:

```json
{
  "urls": ["https://example.com/page"],
  "urlsText": ""
}
```

Response:

```json
{
  "ok": true,
  "data": {
    "jobId": "job-id"
  },
  "jobId": "job-id",
  "rejected": []
}
```
````

## Add URLs To A Job

### `POST /api/jobs/{job_id}/pages/add`

Adds one or more page URLs to an existing job as selected pages.

Request:

```json
{
  "urls": ["https://example.com/extra-page"],
  "urlsText": "https://example.com/another-page"
}
```

Response:

```json
{
  "ok": true,
  "data": [],
  "meta": {
    "count": 2
  },
  "pages": [],
  "rejected": []
}
```

- [ ] **Step 2: Extract save job creation into a helper**

Add this method to `UIServerHandler`:

```python
    def start_save_pages_job(self, urls_text: str, urls_list: list[str] | None = None) -> None:
        combined_text = urls_text
        if urls_list:
            combined_text = "\n".join([combined_text, *[str(url) for url in urls_list if str(url).strip()]])
        urls, rejected = normalize_pasted_urls(combined_text)
        if not urls:
            self.send_api_error(
                "invalid_urls",
                "Paste at least one usable page link.",
                status=HTTPStatus.BAD_REQUEST,
                details={"rejected": rejected},
                rejected=rejected,
            )
            return

        job_id = JOBS.create(
            "scrape",
            source_url=urls[0],
            settings={"mode": "save_pages", "url_count": len(urls)},
        )
        thread = Thread(target=run_scrape_job, args=(job_id, urls, rejected), daemon=True)
        thread.start()
        self.send_api_data({"jobId": job_id}, status=HTTPStatus.ACCEPTED, jobId=job_id, rejected=rejected)
```

- [ ] **Step 3: Replace `/api/scrape` internals with the helper**

Update the `/api/scrape` branch:

```python
if self.path == "/api/scrape":
    payload = self.read_json()
    self.start_save_pages_job(str(payload.get("urlsText", "")))
    return
```

- [ ] **Step 4: Add `/api/jobs/save`**

Add this branch before the `/api/jobs` branch:

```python
if self.path == "/api/jobs/save":
    payload = self.read_json()
    self.start_save_pages_job(str(payload.get("urlsText", "")), urls_list=list(payload.get("urls", [])))
    return
```

- [ ] **Step 5: Run save-flow tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_url_utils.py tests\test_scrape_service.py tests\test_ui_api.py -v
```

Expected: PASS.

### Task 6: Add Query Support For Incremental Events

**Files:**
- Modify: `src/page_scraper/ui_server.py`
- Modify: `docs/api.md`
- Modify: `tests/test_ui_api.py`

- [ ] **Step 1: Add a URL parsing import**

Modify imports in `src/page_scraper/ui_server.py`:

```python
from urllib.parse import parse_qs, urlparse
```

- [ ] **Step 2: Parse path and query at the top of each handler**

At the start of `do_GET`, `do_POST`, and `do_PATCH`, add:

```python
parsed = urlparse(self.path)
path = parsed.path
query = parse_qs(parsed.query)
```

Then compare routes against `path` instead of `self.path`.

- [ ] **Step 3: Use `afterEventId` for events**

In the events branch:

```python
after_event_id = None
if query.get("afterEventId"):
    after_event_id = int(query["afterEventId"][0])
events = [api_event(event) for event in JOBS.events(job_id, after_event_id=after_event_id)]
self.send_api_data(events, meta={"count": len(events)}, events=events)
```

- [ ] **Step 4: Document incremental polling**

Append to `docs/api.md`:

```markdown
## Monitoring

Frontends should poll `GET /api/jobs/{job_id}` for summary state and `GET /api/jobs/{job_id}/events?afterEventId=<last-id>` for incremental updates.

Polling every 500-1000 ms is enough for the local UI. The backend does not expose WebSockets or Server-Sent Events in this phase.
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_job_store.py tests\test_api_contract.py tests\test_ui_api.py -v
```

Expected: PASS.

### Task 7: Return Manifest Contents

**Files:**
- Modify: `src/page_scraper/ui_server.py`
- Modify: `docs/api.md`
- Modify: `tests/test_ui_api.py`

- [ ] **Step 1: Update manifest route behavior**

Change `GET /api/jobs/{job_id}/manifest` to:

```python
manifest_path = write_manifest(JOBS, job_id)
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
self.send_api_data(
    {
        "path": str(manifest_path),
        "manifest": manifest,
    },
    manifest=str(manifest_path),
    path=str(manifest_path),
)
```

- [ ] **Step 2: Document manifest response**

Append to `docs/api.md`:

```markdown
## Manifest

`GET /api/jobs/{job_id}/manifest` writes or refreshes the job manifest and returns both the local path and parsed manifest JSON. The manifest is output metadata, not app persistence.
```

- [ ] **Step 3: Run manifest tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_downloader_manifest.py tests\test_api_contract.py -v
```

Expected: PASS.

### Task 8: Update Frontend-Facing Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/pipeline_notes.md`
- Modify: `Documentation.md`

- [ ] **Step 1: Add README API section**

Add this section to `README.md`:

```markdown
## Local API

The local server exposes a JSON API at `http://127.0.0.1:8765/api/...` for future local frontends. It supports explicit page saves, crawler jobs, selection updates, image variant selection, downloads, job polling, events, failures, and manifest access.

The API is intentionally local and in-memory for now. Restarting the server clears active job state, but downloaded output remains in `data/jobs/<site>_<job-id>/`.

See `docs/api.md` for the current route contract.
```

- [ ] **Step 2: Update pipeline notes**

Add this to `docs/pipeline_notes.md`:

```markdown
## Local API Layer

The local API is a thin JSON layer over the current scraper backend. It does not introduce a database or a separate app framework. Frontends should treat `manifest.json` and files under `data/jobs/` as completed output, while using `/api/jobs/{job_id}` and related routes for live in-memory state.
```

- [ ] **Step 3: Add implementation progress note**

Append to `Documentation.md`:

```markdown
## 2026-05-05 Local API Contract

- Added a stable API contract layer for local frontend callers.
- Kept existing compatibility routes for the simple UI.
- Added normalized response envelopes, frontend-facing job/page/asset/event/failure models, event polling, and manifest JSON responses.
- Kept active job state in memory and completed output in `data/jobs/`.
```

- [ ] **Step 4: Verify docs link together**

Run:

```powershell
Select-String -Path README.md,docs\pipeline_notes.md,Documentation.md,docs\api.md -Pattern "docs/api.md|Local API|data/jobs|in-memory"
```

Expected: output includes all four files.

### Task 9: Add Utility API Endpoints

**Files:**
- Modify: `src/page_scraper/ui_server.py`
- Modify: `src/page_scraper/core/downloader.py`
- Modify: `tests/test_ui_api.py`
- Modify: `docs/api.md`
- Modify: `Documentation.md`

- [ ] **Step 1: Add route tests for utility endpoints**

Extend `tests/test_ui_api.py` with tests for:

```python
def test_add_urls_to_existing_job_adds_selected_pages():
    ...


def test_open_folder_endpoint_allows_job_paths():
    ...


def test_open_folder_endpoint_rejects_non_job_paths():
    ...


def test_retry_failure_endpoint_accepts_recorded_failure():
    ...
```

Expected behavior:

- `POST /api/jobs/{job_id}/pages/add` returns stable `ok/data/meta` and compatibility `pages`.
- `POST /api/system/open-folder` accepts only paths under `data/jobs/`.
- `POST /api/jobs/{job_id}/failures/{failure_id}/retry` accepts a known failure id and starts retry work.

- [ ] **Step 2: Implement `pages/add`**

In `src/page_scraper/ui_server.py`, add a `POST /api/jobs/{job_id}/pages/add` branch that:

- reads `urls` and `urlsText`;
- normalizes them with `normalize_pasted_urls`;
- calls `JOBS.upsert_page(..., selected=True, status="discovered")`;
- returns added pages through `api_page(...)` plus compatibility `pages` and `rejected`.

- [ ] **Step 3: Implement guarded folder opening**

Add `open_local_folder(path: str) -> str` in `src/page_scraper/ui_server.py`.

Rules:

- resolve the requested path;
- if a file path is provided, use its parent folder;
- allow only `data/jobs/` or descendants;
- reject missing folders;
- call `os.startfile(...)` on Windows.

Expose it through `POST /api/system/open-folder`.

- [ ] **Step 4: Implement failure retry**

Add `retry_failure(job_id, failure_id)` and `run_retry_failure_job(...)` in `src/page_scraper/ui_server.py`.

Rules:

- find the recorded failure from `JOBS.failures(job_id)`;
- support `related_type == "page"` and `related_type == "asset"`;
- reset the target item to `status="discovered"` and clear `error_message`;
- mark that item selected;
- start the existing downloader in a background thread.

- [ ] **Step 5: Avoid re-saving completed selected items**

Update `src/page_scraper/core/downloader.py` so selected pages/assets with `status == "downloaded"` are skipped.

- [ ] **Step 6: Document the utility endpoints**

Update `docs/api.md` and `Documentation.md` with:

- `POST /api/jobs/{job_id}/pages/add`
- `POST /api/system/open-folder`
- `POST /api/jobs/{job_id}/failures/{failure_id}/retry`

- [ ] **Step 7: Run focused utility endpoint tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ui_api.py -v
```

Expected: PASS.

### Task 10: Manual API Smoke Test

**Files:**
- No source edits.

- [ ] **Step 1: Run the focused backend tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_contract.py tests\test_ui_api.py tests\test_job_store.py tests\test_crawler.py tests\test_downloader_manifest.py -v
```

Expected: PASS.

- [ ] **Step 2: Run the existing broader test set**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

Expected: PASS. If `pytest` is unavailable in this repo, run the current manual test command used by the project and record the exact command/output in `Documentation.md`.

- [ ] **Step 3: Launch the local server**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\launch_ui.py --no-browser
```

Expected: terminal prints `Page Saver is running at http://127.0.0.1:8765`.

- [ ] **Step 4: Check health**

In a second PowerShell:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8765/api/health
```

Expected: response has `ok = True`, `data.apiVersion = 1`, and capabilities.

- [ ] **Step 5: Create a crawl job**

Run:

```powershell
$job = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/api/jobs -ContentType 'application/json' -Body '{"sourceUrl":"https://jegged.com/Games/Final-Fantasy-X/","maxDepth":1,"sameDomainOnly":true,"stayUnderStartPath":true,"includeImages":true,"includeDocuments":true,"includeVideo":false}'
$job.jobId
```

Expected: prints a job id.

- [ ] **Step 6: Start discovery**

Run:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8765/api/jobs/$($job.jobId)/discover"
```

Expected: accepted response with the same job id.

- [ ] **Step 7: Poll job and events**

Run:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8765/api/jobs/$($job.jobId)"
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8765/api/jobs/$($job.jobId)/events?afterEventId=0"
```

Expected: job summary shows pages/assets counts after discovery completes; events return incremental records.

- [ ] **Step 8: Download selected**

Run:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8765/api/jobs/$($job.jobId)/download"
```

Expected: accepted response. Poll the job until status is `completed` or `completed_with_errors`.

- [ ] **Step 9: Read manifest**

Run:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8765/api/jobs/$($job.jobId)/manifest"
```

Expected: response includes `data.path` and `data.manifest`.

- [ ] **Step 10: Exercise utility routes**

Run a quick route-level test:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ui_api.py -v
```

Expected: PASS, including the add-URL, open-folder guard, and retry-failure endpoint tests.

## Verification Checklist

- [ ] The plan does not add SQLite, DB schemas, migrations, repositories, or restart-safe job history.
- [ ] Current simple UI routes still work.
- [ ] New frontend-facing responses include stable `ok`, `data`, and `error` envelopes.
- [ ] Compatibility keys remain during transition.
- [ ] Job output still writes to `data/jobs/<site>_<job-id>/`.
- [ ] Docs state that active jobs are in memory only.
- [ ] Tests cover contract helpers and route behavior.
- [ ] Tests cover `pages/add`, guarded `open-folder`, and failure retry.
