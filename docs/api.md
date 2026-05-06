# Local Page Scraper API

The local API is served by `scripts/launch_ui.py` at `http://127.0.0.1:8765` by default.

This API is intended for local frontends. It does not use a database. Active jobs live in memory while the server is running. Downloaded output is written to `data/jobs/<site>_<job-id>/`, and completed job summaries are represented by `manifest.json`.

Developer diagnostics are written with Python standard-library logging to `logs/page_scraper.log` when the UI server starts. API clients should keep using `/api/jobs/{job_id}/events`, `/api/jobs/{job_id}/failures`, and `/api/jobs/{job_id}/manifest` for user-facing status.

## Current Compatibility Routes

- `GET /ping`
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

## Response Shape

New frontend code should read the stable response envelope:

```json
{
  "ok": true,
  "data": {}
}
```

Errors use the same shape everywhere:

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

Some routes still include compatibility keys such as `jobId`, `pages`, `assets`, `events`, and `failures` so the current simple UI keeps working while the frontend contract settles.

## Ping

### `GET /ping`

Returns a minimal server-alive response for frontend sanity checks. This route does not inspect jobs, touch saved output, or perform scraper work.

Response:

```json
{
  "ok": true,
  "data": {
    "status": "up",
    "service": "page-scraper",
    "apiVersion": "1"
  }
}
```

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

`POST /api/scrape` remains available as the older compatibility route for the simple UI.

## Add URLs To A Job

### `POST /api/jobs/{job_id}/pages/add`

Adds one or more page URLs to an existing job as selected pages. This is the backend route for a future `+ Add URL` UI affordance.

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

## Monitoring

Frontends should poll `GET /api/jobs/{job_id}` for summary state and `GET /api/jobs/{job_id}/events?afterEventId=<last-id>` for incremental updates.

Polling every 500-1000 ms is enough for the local UI. The backend does not expose WebSockets or Server-Sent Events in this phase.

## Manifest

`GET /api/jobs/{job_id}/manifest` writes or refreshes the job manifest and returns both the local path and parsed manifest JSON. The manifest is output metadata, not app persistence.

## Open Output Folder

### `POST /api/system/open-folder`

Opens a local job output folder on Windows. For safety, this endpoint only accepts folders inside `data/jobs/`.

Request:

```json
{
  "path": "data/jobs/jegged_abcdef12"
}
```

## Failure Retry

### `POST /api/jobs/{job_id}/failures/{failure_id}/retry`

Re-queues the page or file connected to a recorded failure and starts the existing downloader in the background. This is intentionally narrow for v1: it retries failures tied to known page or asset records.
