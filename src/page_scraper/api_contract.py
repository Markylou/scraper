from __future__ import annotations

from datetime import UTC, datetime
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


def _camel_key(key: str) -> str:
    parts = key.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def api_settings(settings: dict) -> dict:
    return {_camel_key(key): value for key, value in settings.items()}


def api_timestamp(value: Any) -> Any:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, UTC).isoformat()
    return value


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
        "settings": api_settings(job.get("settings", {})),
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
        "createdAt": api_timestamp(job.get("created_at")),
        "updatedAt": api_timestamp(job.get("updated_at")),
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
