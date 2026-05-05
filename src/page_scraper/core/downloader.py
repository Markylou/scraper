from __future__ import annotations

import hashlib
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from ..fetch_requests import USER_AGENT, fetch_url
from ..page_archive import archive_page, page_slug_from_title
from .job_output import job_output_root
from .manifest import write_manifest


REQUEST_TIMEOUT_SECONDS = 30
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024


def default_fetch_page_html(url: str) -> str:
    return fetch_url(url).html


def default_fetch_asset(url: str) -> tuple[bytes, str | None]:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    body = response.content
    if len(body) > MAX_FILE_SIZE_BYTES:
        raise ValueError("file too large")
    return body, response.headers.get("Content-Type")


def asset_filename(url: str) -> str:
    parsed = urlparse(url)
    name = parsed.path.rsplit("/", 1)[-1] or "asset"
    stem = name.rsplit(".", 1)[0] if "." in name else name
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"{page_slug_from_title(stem)}-{digest}{ext.lower()}"


def asset_subdir(asset_type: str) -> str:
    if asset_type == "image":
        return "images"
    if asset_type == "document":
        return "documents"
    return "other"


def download_selected(
    store,
    job_id: str,
    jobs_dir=None,
    fetch_page_html=default_fetch_page_html,
    fetch_asset=default_fetch_asset,
) -> dict:
    job = store.get(job_id)
    root = job_output_root(job["source_url"], job_id, jobs_dir=jobs_dir) if jobs_dir else job_output_root(job["source_url"], job_id)
    pages_root = root / "pages"
    assets_root = root / "assets"
    root.mkdir(parents=True, exist_ok=True)
    store.set_output_root(job_id, str(root))
    store.set_status(job_id, "downloading")
    store.event(job_id, "info", "download_started", "Downloading selected items", {"output_root": str(root)})

    pages_downloaded = 0
    assets_downloaded = 0

    for page in store.pages(job_id):
        if store.is_cancelled(job_id):
            break
        if store.is_paused(job_id):
            break
        if not page.get("selected", True):
            continue
        store.event(job_id, "info", "file_started", "Saving page", {"url": page["url"]})
        try:
            html = fetch_page_html(page["url"])
            archive = archive_page(
                url=page["url"],
                final_url=page["normalized_url"],
                title=page.get("title") or page["url"],
                html=html,
                strategy="download",
                pages_dir=pages_root,
            )
            local_path = archive.source_file.relative_to(root).as_posix()
            store.update_page(job_id, page["id"], status="downloaded", local_path=local_path, size_bytes=len(html.encode("utf-8")))
            pages_downloaded += 1
            store.event(job_id, "info", "file_completed", "Saved page", {"url": page["url"], "path": local_path})
        except Exception as exc:
            store.update_page(job_id, page["id"], status="failed", error_message=str(exc))
            store.failure(job_id, "page", page["id"], page["url"], failure_code(exc), str(exc))
            store.event(job_id, "error", "file_failed", "Page could not be saved", {"url": page["url"]})

    for asset in store.assets(job_id):
        if store.is_cancelled(job_id):
            break
        if store.is_paused(job_id):
            break
        if not asset.get("selected", False):
            continue
        store.event(job_id, "info", "file_started", "Saving file", {"url": asset["url"]})
        try:
            body, content_type = fetch_with_retries(asset["url"], fetch_asset)
            target_dir = assets_root / asset_subdir(asset["asset_type"])
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / asset_filename(asset["url"])
            target.write_bytes(body)
            local_path = target.relative_to(root).as_posix()
            store.update_asset(
                job_id,
                asset["id"],
                status="downloaded",
                local_path=local_path,
                content_type=content_type,
                size_bytes=len(body),
            )
            assets_downloaded += 1
            store.event(job_id, "info", "file_completed", "Saved file", {"url": asset["url"], "path": local_path})
        except Exception as exc:
            store.update_asset(job_id, asset["id"], status="failed", error_message=str(exc))
            store.failure(job_id, "asset", asset["id"], asset["url"], failure_code(exc), str(exc))
            store.event(job_id, "error", "file_failed", "File could not be saved", {"url": asset["url"]})

    if store.is_cancelled(job_id):
        status = "cancelled"
    elif store.is_paused(job_id):
        status = "paused"
    elif blocking_failures(store.failures(job_id)):
        status = "completed_with_errors"
    else:
        status = "completed"
    store.set_status(job_id, status)
    write_manifest(store, job_id)
    store.event(job_id, "info", "job_completed", "Download finished", {"status": status})
    return {
        "ok": status in {"completed", "completed_with_errors"},
        "output_root": str(root),
        "pages_downloaded": pages_downloaded,
        "assets_downloaded": assets_downloaded,
        "failures": len(store.failures(job_id)),
    }


def fetch_with_retries(url: str, fetch_asset) -> tuple[bytes, str | None]:
    last_error: Exception | None = None
    for delay in [0, 1, 3]:
        if delay:
            time.sleep(delay)
        try:
            return fetch_asset(url)
        except Exception as exc:
            last_error = exc
    raise last_error or RuntimeError("unknown download error")


def failure_code(exc: Exception) -> str:
    message = str(exc).lower()
    if "404" in message:
        return "http_404"
    if "timeout" in message:
        return "timeout"
    if "too large" in message:
        return "file_too_large"
    return "network_error"


def blocking_failures(failures: list[dict]) -> list[dict]:
    return [
        failure
        for failure in failures
        if not str(failure.get("failure_code", "")).startswith("skipped_")
    ]
