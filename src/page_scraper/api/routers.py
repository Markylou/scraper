from __future__ import annotations

import json
from pathlib import Path
from threading import Thread
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from page_scraper.api.dependencies import get_job_store, require_job
from page_scraper.api.models import (
    AddPagesRequest,
    CreateJobRequest,
    SavePagesRequest,
)
from page_scraper.content_builder import main as rebuild_page_content
from page_scraper.core.crawler import DiscoverySettings, discover
from page_scraper.core.downloader import download_selected
from page_scraper.core.job_output import job_output_root
from page_scraper.core.manifest import write_manifest
from page_scraper.job_store import JobStore
from page_scraper.logging_config import get_logger
from page_scraper.paths import JOBS_DIR
from page_scraper.scrape_service import scrape_urls
from page_scraper.url_utils import normalize_pasted_urls


LOGGER = get_logger("api.routers")
api_router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# Helper functions (now accept job_store)
# ──────────────────────────────────────────────────────────────────────────────

def run_scrape_job(job_id: str, urls: list[str], rejected: list[str], job_store: JobStore) -> None:
    def progress(message: str) -> None:
        job_store.log(job_id, message)

    root = job_output_root(urls[0], job_id)
    pages_root = root / "pages"
    job_store.set_output_root(job_id, str(root))
    job_store.set_status(job_id, "downloading")
    job_store.event(job_id, "info", "save_started", "Saving pasted pages", {"output_root": str(root)})

    outcomes = scrape_urls(
        urls,
        progress=progress,
        pages_dir=pages_root,
        display_root=f"data/jobs/{root.name}/pages",
    )

    for outcome in outcomes:
        if outcome.ok and outcome.saved_folder:
            page = job_store.upsert_page(job_id, outcome.url, 0, None, title=outcome.url, status="downloaded")
            source_file = pages_root / outcome.saved_folder / "source.html"
            job_store.update_page(
                job_id,
                page["id"],
                local_path=f"pages/{outcome.saved_folder}/source.html",
                size_bytes=source_file.stat().st_size if source_file.exists() else None,
            )
        else:
            job_store.failure(job_id, "page", None, outcome.url, "save_failed", outcome.message)

    failed_count = len([o for o in outcomes if not o.ok])
    status = "completed_with_errors" if failed_count or rejected else "completed"
    job_store.set_status(job_id, status)
    write_manifest(job_store, job_id)
    job_store.finish(
        job_id,
        {
            "ok": failed_count == 0,
            "saved": [outcome.to_dict() for outcome in outcomes],
            "rejected": rejected,
            "output_root": str(root),
            "manifest": str(root / "manifest.json"),
        },
        status="done",
    )


def run_discovery_job(job_id: str, job_store: JobStore) -> None:
    try:
        result = discover(job_store, job_id)
        job = job_store.get(job_id)
        job_status = job["status"]
        job_store.finish(job_id, result, status="done" if job_status == "ready" else job_status)
    except Exception as exc:
        LOGGER.exception("Discovery job failed")
        job_store.fail(job_id, str(exc))


def run_download_job(job_id: str, job_store: JobStore) -> None:
    try:
        result = download_selected(job_store, job_id)
        job = job_store.get(job_id)
        job_status = job["status"]
        job_store.finish(job_id, result, status="done" if job_status in {"completed", "completed_with_errors"} else job_status)
    except Exception as exc:
        LOGGER.exception("Download job failed")
        job_store.fail(job_id, str(exc))


def retry_failure(job_id: str, failure_id: str, job_store: JobStore) -> dict:
    failure = next((item for item in job_store.failures(job_id) if item["id"] == failure_id), None)
    if not failure:
        raise ValueError("Failure was not found.")

    related_type = failure.get("related_type")
    related_id = failure.get("related_id")
    url = failure.get("url")

    if related_type == "page":
        page = next((item for item in job_store.pages(job_id) if item["id"] == related_id), None)
        if page is None and url:
            page = job_store.upsert_page(job_id, url, 0, None, status="discovered")
        if page is None:
            raise ValueError("Could not find the page to retry.")
        job_store.update_page(job_id, page["id"], status="discovered", error_message=None)
        job_store.set_page_selection(job_id, [page["id"]], True)
        return {"related_type": "page", "related_id": page["id"]}

    if related_type == "asset":
        asset = next((item for item in job_store.assets(job_id) if item["id"] == related_id), None)
        if asset is None:
            raise ValueError("Could not find the file to retry.")
        job_store.update_asset(job_id, asset["id"], status="discovered", error_message=None)
        job_store.set_asset_selection(job_id, [asset["id"]], True)
        return {"related_type": "asset", "related_id": asset["id"]}

    raise ValueError("This failure type cannot be retried.")


def run_retry_failure_job(job_id: str, retry: dict, job_store: JobStore) -> None:
    try:
        related_type = retry["related_type"]
        related_id = retry["related_id"]

        page_selection = {page["id"]: page.get("selected", True) for page in job_store.pages(job_id)}
        asset_selection = {asset["id"]: asset.get("selected", False) for asset in job_store.assets(job_id)}

        if page_selection:
            job_store.set_page_selection(job_id, list(page_selection), False)
        if asset_selection:
            job_store.set_asset_selection(job_id, list(asset_selection), False)

        if related_type == "page":
            job_store.set_page_selection(job_id, [related_id], True)
        if related_type == "asset":
            job_store.set_asset_selection(job_id, [related_id], True)

        result = download_selected(job_store, job_id)

        for page_id, selected in page_selection.items():
            job_store.set_page_selection(job_id, [page_id], selected)
        for asset_id, selected in asset_selection.items():
            job_store.set_asset_selection(job_id, [asset_id], selected)

        job_store.finish(job_id, result, status="done" if job_store.get(job_id)["status"] in {"completed", "completed_with_errors"} else job_store.get(job_id)["status"])
    except Exception as exc:
        LOGGER.exception("Retry failure job failed")
        job_store.fail(job_id, str(exc))


def open_local_folder(path: str) -> str:
    target = Path(path).expanduser().resolve()
    if target.is_file():
        target = target.parent
    jobs_root = JOBS_DIR.resolve()
    if target != jobs_root and jobs_root not in target.parents:
        raise ValueError("Only job output folders can be opened.")
    if not target.exists() or not target.is_dir():
        raise ValueError("Folder was not found.")
    import os
    os.startfile(str(target))
    return str(target)


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@api_router.get("/health")
async def health(job_store: JobStore = Depends(get_job_store)):
    return {
        "ok": True,
        "data": {
            "server": "PageScraperUI/0.1",
            "apiVersion": "1",
            "capabilities": [
                "save-pages",
                "refresh-content",
                "discover-pages",
                "download-selected",
                "image-variant-selection",
            ],
        },
    }


@api_router.post("/scrape")
@api_router.post("/jobs/save")
async def save_pages(
    payload: SavePagesRequest,
    background_tasks: BackgroundTasks,
    job_store: JobStore = Depends(get_job_store),
):
    combined_text = payload.urlsText or ""
    if payload.urls:
        combined_text = "\n".join([combined_text, *[str(u) for u in payload.urls if str(u).strip()]])

    urls, rejected = normalize_pasted_urls(combined_text)
    if not urls:
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "error": {"code": "invalid_urls", "message": "Paste at least one usable page link."},
                "rejected": rejected,
            },
        )

    job_id = job_store.create(
        "scrape",
        source_url=urls[0],
        settings={"mode": "save_pages", "url_count": len(urls)},
    )
    thread = Thread(target=run_scrape_job, args=(job_id, urls, rejected, job_store), daemon=True)
    thread.start()

    return JSONResponse(
        status_code=202,
        content={
            "ok": True,
            "data": {"jobId": job_id},
            "jobId": job_id,
            "rejected": rejected,
        },
    )


@api_router.post("/jobs")
async def create_job(
    payload: CreateJobRequest,
    job_store: JobStore = Depends(get_job_store),
):
    source_url = payload.sourceUrl.strip()
    if not source_url:
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "error": {"code": "invalid_request", "message": "Enter a starting page link."},
            },
        )

    settings = DiscoverySettings(
        max_depth=payload.maxDepth,
        same_domain_only=payload.sameDomainOnly,
        stay_under_start_path=payload.stayUnderStartPath,
        include_images=payload.includeImages,
        include_documents=payload.includeDocuments,
        include_video=payload.includeVideo,
    ).to_dict()

    job_id = job_store.create("crawl", status="created", source_url=source_url, settings=settings)
    job = job_store.get(job_id)
    from page_scraper.api_contract import api_job

    return JSONResponse(
         status_code=202,
         content={
               "ok": True,
               "data": api_job(job),
               "jobId": job_id,
               "job": job,
         },
      )


@api_router.post("/jobs/{job_id}/discover")
async def start_discovery(
    job_id: str = Depends(require_job),
    job_store: JobStore = Depends(get_job_store),
):
    thread = Thread(target=run_discovery_job, args=(job_id, job_store), daemon=True)
    thread.start()
    return {"ok": True, "data": {"jobId": job_id}, "jobId": job_id}


@api_router.post("/jobs/{job_id}/download")
async def start_download(
    job_id: str = Depends(require_job),
    job_store: JobStore = Depends(get_job_store),
):
    thread = Thread(target=run_download_job, args=(job_id, job_store), daemon=True)
    thread.start()
    return {"ok": True, "data": {"jobId": job_id}, "jobId": job_id}


@api_router.get("/jobs/{job_id}")
async def get_job(
    job_id: str = Depends(require_job),
    job_store: JobStore = Depends(get_job_store),
):
    job = job_store.get(job_id)
    from page_scraper.api_contract import api_job
    return {"ok": True, "data": api_job(job), "status": job.get("status"), "job": job}


@api_router.get("/jobs/{job_id}/pages")
async def get_pages(
    job_id: str = Depends(require_job),
    job_store: JobStore = Depends(get_job_store),
):
    pages = job_store.pages(job_id)
    from page_scraper.api_contract import api_page
    api_pages = [api_page(p) for p in pages]
    return {"ok": True, "data": api_pages, "meta": {"count": len(api_pages)}, "pages": pages}


@api_router.get("/jobs/{job_id}/assets")
async def get_assets(
    job_id: str = Depends(require_job),
    job_store: JobStore = Depends(get_job_store),
):
    assets = job_store.assets(job_id)
    from page_scraper.api_contract import api_asset
    api_assets = [api_asset(a) for a in assets]
    return {"ok": True, "data": api_assets, "meta": {"count": len(api_assets)}, "assets": assets}


@api_router.patch("/jobs/{job_id}/pages/selection")
async def update_page_selection(
    job_id: str = Depends(require_job),
    payload: dict = ...,
    job_store: JobStore = Depends(get_job_store),
):
    ids = payload.get("ids", [])
    selected = payload.get("selected", True)
    job_store.set_page_selection(job_id, ids, selected)
    pages = job_store.pages(job_id)
    from page_scraper.api_contract import api_page
    return {"ok": True, "data": [api_page(p) for p in pages], "meta": {"count": len(pages)}, "pages": pages}


@api_router.patch("/jobs/{job_id}/assets/selection")
async def update_asset_selection(
    job_id: str = Depends(require_job),
    payload: dict = ...,
    job_store: JobStore = Depends(get_job_store),
):
    ids = payload.get("ids", [])
    selected = payload.get("selected", True)
    job_store.set_asset_selection(job_id, ids, selected)
    assets = job_store.assets(job_id)
    from page_scraper.api_contract import api_asset
    return {"ok": True, "data": [api_asset(a) for a in assets], "meta": {"count": len(assets)}, "assets": assets}


@api_router.patch("/jobs/{job_id}/assets/variant")
async def set_asset_variant(
    job_id: str = Depends(require_job),
    payload: dict = ...,
    job_store: JobStore = Depends(get_job_store),
):
    asset_id = payload.get("assetId", "")
    url = payload.get("url", "")
    job_store.set_asset_variant(job_id, asset_id, url)
    assets = job_store.assets(job_id)
    from page_scraper.api_contract import api_asset
    return {"ok": True, "data": [api_asset(a) for a in assets], "meta": {"count": len(assets)}, "assets": assets}


@api_router.get("/jobs/{job_id}/events")
async def get_events(
    job_id: str = Depends(require_job),
    afterEventId: int | None = Query(None),
    job_store: JobStore = Depends(get_job_store),
):
    events = job_store.events(job_id, after_event_id=afterEventId)
    from page_scraper.api_contract import api_event
    return {"ok": True, "data": [api_event(e) for e in events], "meta": {"count": len(events)}, "events": events}


@api_router.get("/jobs/{job_id}/failures")
async def get_failures(
    job_id: str = Depends(require_job),
    job_store: JobStore = Depends(get_job_store),
):
    failures = job_store.failures(job_id)
    from page_scraper.api_contract import api_failure
    return {"ok": True, "data": [api_failure(f) for f in failures], "meta": {"count": len(failures)}, "failures": failures}


@api_router.get("/jobs/{job_id}/manifest")
async def get_manifest(
    job_id: str = Depends(require_job),
    job_store: JobStore = Depends(get_job_store),
):
    manifest_path = write_manifest(job_store, job_id)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "ok": True,
        "data": {"path": str(manifest_path), "manifest": manifest},
        "manifest": str(manifest_path),
        "path": str(manifest_path),
    }


@api_router.post("/jobs/{job_id}/pages/add")
async def add_pages_to_job(
    job_id: str = Depends(require_job),
    payload: AddPagesRequest = ...,
    job_store: JobStore = Depends(get_job_store),
):
    combined_text = payload.urlsText or ""
    if payload.urls:
        combined_text = "\n".join([combined_text, *[str(u) for u in payload.urls if str(u).strip()]])

    urls, rejected = normalize_pasted_urls(combined_text)
    if not urls:
        raise HTTPException(
            status_code=400,
            detail={"ok": False, "error": {"code": "invalid_urls", "message": "Add at least one usable page link."}, "rejected": rejected},
        )

    added = []
    for url in urls:
        added.append(job_store.upsert_page(job_id, url, 0, None, title=url, status="discovered", selected=True))

    from page_scraper.api_contract import api_page
    return {"ok": True, "data": [api_page(p) for p in added], "meta": {"count": len(added)}, "pages": added, "rejected": rejected}


@api_router.post("/jobs/{job_id}/pause")
async def pause_job(
    job_id: str = Depends(require_job),
    job_store: JobStore = Depends(get_job_store),
):
    job_store.pause(job_id)
    job = job_store.get(job_id)
    from page_scraper.api_contract import api_job
    return {"ok": True, "data": api_job(job), "job": job}


@api_router.post("/jobs/{job_id}/resume")
async def resume_job(
    job_id: str = Depends(require_job),
    job_store: JobStore = Depends(get_job_store),
):
    job_store.resume(job_id)
    job = job_store.get(job_id)
    from page_scraper.api_contract import api_job
    return {"ok": True, "data": api_job(job), "job": job}


@api_router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str = Depends(require_job),
    job_store: JobStore = Depends(get_job_store),
):
    job_store.cancel(job_id)
    job = job_store.get(job_id)
    from page_scraper.api_contract import api_job
    return {"ok": True, "data": api_job(job), "job": job}


@api_router.post("/jobs/{job_id}/failures/{failure_id}/retry")
async def retry_failure_endpoint(
    job_id: str = Depends(require_job),
    failure_id: str = ...,
    job_store: JobStore = Depends(get_job_store),
):
    try:
        retry = retry_failure(job_id, failure_id, job_store)
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"ok": False, "error": {"code": "retry_failed", "message": str(exc)}})

    thread = Thread(target=run_retry_failure_job, args=(job_id, retry, job_store), daemon=True)
    thread.start()
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=202,
        content={
            "ok": True,
            "data": {"jobId": job_id, "failureId": failure_id},
            "jobId": job_id,
            "failureId": failure_id,
        },
    )


@api_router.post("/build/page-content")
async def build_page_content(
    background_tasks: BackgroundTasks,
    job_store: JobStore = Depends(get_job_store),
):
    job_id = job_store.create("build-page-content")
    thread = Thread(target=lambda: job_store.finish(job_id, rebuild_page_content() or {"ok": True}), daemon=True)
    thread.start()
    return {"ok": True, "data": {"jobId": job_id}, "jobId": job_id}


@api_router.post("/system/open-folder")
async def open_folder(payload: dict):
    try:
        opened = open_local_folder(str(payload.get("path", "")))
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"ok": False, "error": {"code": "invalid_path", "message": str(exc)}})
    return {"ok": True, "data": {"path": opened}}