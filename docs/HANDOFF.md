# Handoff

## Project
- Local Python crawler/web scraper backend for saving pages, discovering links/assets, downloading selected output, and serving a local API for a separate SolidJS/Vite frontend.
- The project is no longer intended to be FFXIII-2-only. Preserve the generalized `page_scraper` direction.

## Current State
- Main working repo inspected here: `D:\root\projects\scraper`, branch `codex-browser-scraper-ui`, clean except untracked `codex-skills/`.
- FastAPI migration copy: `D:\root\code\scraper`, branch `codex/fastapi-migration`, clean and pushed to `origin/codex/fastapi-migration` at commit `42d0e11`.
- FastAPI migration already added `fastapi`, `uvicorn[standard]`, and `httpx` to `requirements.txt`.
- FastAPI files exist under `D:\root\code\scraper\src\page_scraper\api\`: `app.py`, `dependencies.py`, `models.py`, `routers.py`.

## Recent Decisions
- Keep jobs in memory for now; no SQLite or durable job history in this phase.
- Keep downloaded output in `data/jobs/<site>_<job-id>/` with `manifest.json`.
- Preserve the stable JSON envelope: success is `{ "ok": true, "data": ... }`; errors are `{ "ok": false, "error": ... }`.
- Preserve compatibility keys such as `jobId`, `pages`, `assets`, `events`, and `failures` while the frontend settles.
- Keep polling for now; do not add WebSockets/SSE yet.
- Add/keep CORS for local Vite origins such as `http://localhost:5173` and `http://127.0.0.1:5173`.

## Key Files
- `D:\root\code\scraper\src\page_scraper\api\app.py`: FastAPI app factory, CORS, `/ping`, docs routes, exception envelopes, uvicorn startup.
- `D:\root\code\scraper\src\page_scraper\api\routers.py`: Migrated endpoint logic and background job dispatch.
- `D:\root\code\scraper\src\page_scraper\api\models.py`: Pydantic request/response model start; likely needs review/expansion.
- `D:\root\code\scraper\scripts\launch_ui.py`: Now starts the FastAPI app through uvicorn.
- `D:\root\projects\scraper\docs\api.md`: Source-of-truth API route list and response expectations before/alongside FastAPI migration.

## Commands
- `cd D:\root\code\scraper`: work in the FastAPI migration copy.
- `git status --short --branch`: confirm branch is `codex/fastapi-migration`.
- `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`: install FastAPI migration dependencies.
- `.\.venv\Scripts\python.exe scripts\launch_ui.py`: start backend at `http://127.0.0.1:8765`.
- `.\.venv\Scripts\python.exe -m pytest tests -v`: run backend tests.

## Open Work
1. Review the FastAPI migration for endpoint parity with `docs/api.md`.
2. Run the full test suite in `D:\root\code\scraper`; this handoff did not run it.
3. Open `http://127.0.0.1:8765/docs`, `/redoc`, `/openapi.json`, and `/ping` after launch.
4. Verify SolidJS/Vite can create a job, read `jobId` or `data.id`, start discovery, poll job state, list pages/assets, and download selected items.
5. Suggest improvements to Pydantic response models and OpenAPI docs without breaking the current envelope/compatibility keys.

## Watchouts
- Do not work on `main`; it is an older snapshot. Use `codex-browser-scraper-ui` for the pre-FastAPI branch and `codex/fastapi-migration` for the migration.
- Earlier frontend bug: it called `/api/jobs/undefined/discover`. Frontend should resolve job id from `jobId`, `data.id`, or `job.id` and guard before job-specific calls.
- Earlier backend bug: compatibility field `status` once clobbered HTTP status. Keep HTTP status variables distinct from JSON job status.
- Earlier store issue: emitting events while holding `JobStore` lock caused deadlock. Avoid nested lock calls in job-store changes.
- `POST /api/system/open-folder` must stay guarded to folders inside `data/jobs/`.
