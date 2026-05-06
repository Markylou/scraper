# Local Page Scraper API

The local API is now served by **FastAPI** via `scripts/launch_ui.py` at `http://127.0.0.1:8765` by default.

This API is intended for local frontends (SolidJS/Vite during development). It does not use a database. Active jobs live in memory while the server is running. Downloaded output is written to `data/jobs/<site>_<job-id>/`, and completed job summaries are represented by `manifest.json`.

**OpenAPI Documentation** (recommended):
- Swagger UI: http://127.0.0.1:8765/docs
- ReDoc: http://127.0.0.1:8765/redoc
- OpenAPI schema: http://127.0.0.1:8765/openapi.json

Developer diagnostics are written with Python standard-library logging to `logs/page_scraper.log`.

## Response Shape

All successful responses use the stable envelope:

```json
{
  "ok": true,
  "data": {}
}
```

Errors:

```json
{
  "ok": false,
  "error": {
    "code": "invalid_request",
    "message": "...",
    "details": {}
  }
}
```

Some routes still return compatibility keys (`jobId`, `job`, `pages`, `assets`, etc.) so existing frontends continue to work without changes.

## Core Routes

### Health & Ping
- `GET /ping`
- `GET /api/health`

### Job Management
- `POST /api/jobs` — Create a new crawl job
- `POST /api/jobs/save` (also `POST /api/scrape` for compatibility)
- `GET /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/discover`
- `POST /api/jobs/{job_id}/download`
- `POST /api/jobs/{job_id}/pause`
- `POST /api/jobs/{job_id}/resume`
- `POST /api/jobs/{job_id}/cancel`
- `POST /api/jobs/{job_id}/pages/add`
- `PATCH /api/jobs/{job_id}/pages/selection`
- `PATCH /api/jobs/{job_id}/assets/selection`
- `PATCH /api/jobs/{job_id}/assets/variant`

### Monitoring
- `GET /api/jobs/{job_id}/pages`
- `GET /api/jobs/{job_id}/assets`
- `GET /api/jobs/{job_id}/events?afterEventId=...`
- `GET /api/jobs/{job_id}/failures`
- `GET /api/jobs/{job_id}/manifest`
- `POST /api/jobs/{job_id}/failures/{failure_id}/retry`

### Utilities
- `POST /api/build/page-content`
- `POST /api/system/open-folder`

See the interactive docs at `/docs` for full requestresponse schemas.
