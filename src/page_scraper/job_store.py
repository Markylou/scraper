from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from time import time
from uuid import uuid4

from .core.normalizer import normalize_url, url_identity_key


ACTIVE_STATUSES = {"created", "discovering", "ready", "downloading", "paused", "running"}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Job:
    id: str
    type: str
    status: str = "running"
    messages: list[str] = field(default_factory=list)
    result: dict | None = None
    error: str | None = None
    created_at: float = field(default_factory=time)
    updated_at: float = field(default_factory=time)
    source_url: str | None = None
    normalized_source_url: str | None = None
    settings: dict = field(default_factory=dict)
    output_root: str | None = None
    events: list[dict] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    pages: dict[str, dict] = field(default_factory=dict)
    assets: dict[str, dict] = field(default_factory=dict)
    paused: bool = False
    cancelled: bool = False


class JobStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, Job] = {}
        self._event_counter = 0

    def create(
        self,
        job_type: str,
        status: str = "running",
        source_url: str | None = None,
        settings: dict | None = None,
    ) -> str:
        job_id = uuid4().hex
        normalized = normalize_url(source_url) if source_url else None
        with self._lock:
            self._jobs[job_id] = Job(
                id=job_id,
                type=job_type,
                status=status,
                source_url=source_url,
                normalized_source_url=normalized,
                settings=settings or {},
            )
        self.event(job_id, "info", "job_created", "Job created")
        return job_id

    def exists(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._jobs

    def log(self, job_id: str, message: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.messages.append(message)
            job.updated_at = time()
        self.event(job_id, "info", "message", message)

    def set_status(self, job_id: str, status: str, message: str | None = None) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = status
            job.updated_at = time()
            if message:
                job.messages.append(message)

    def finish(self, job_id: str, result: dict, status: str = "done") -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = status
            job.result = result
            job.updated_at = time()
        self.event(job_id, "info", "job_completed", "Job completed", {"status": status})

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "error"
            job.error = error
            job.updated_at = time()
        self.failure(job_id, "job", job_id, None, "unknown_error", error)
        self.event(job_id, "error", "job_failed", error)

    def event(self, job_id: str, level: str, event_type: str, message: str, metadata: dict | None = None) -> dict:
        with self._lock:
            self._event_counter += 1
            event = {
                "id": self._event_counter,
                "job_id": job_id,
                "level": level,
                "event_type": event_type,
                "message": message,
                "metadata": metadata or {},
                "created_at": now_iso(),
            }
            self._jobs[job_id].events.append(event)
            self._jobs[job_id].updated_at = time()
            return dict(event)

    def failure(
        self,
        job_id: str,
        related_type: str,
        related_id: str | None,
        url: str | None,
        failure_code: str,
        message: str,
        details: dict | None = None,
    ) -> dict:
        with self._lock:
            failure = {
                "id": uuid4().hex,
                "job_id": job_id,
                "related_type": related_type,
                "related_id": related_id,
                "url": url,
                "failure_code": failure_code,
                "message": message,
                "details": details or {},
                "created_at": now_iso(),
            }
            self._jobs[job_id].failures.append(failure)
            self._jobs[job_id].updated_at = time()
            return dict(failure)

    def upsert_page(
        self,
        job_id: str,
        url: str,
        depth: int,
        discovered_from_url: str | None,
        title: str | None = None,
        status: str = "discovered",
        selected: bool = True,
    ) -> dict:
        normalized = normalize_url(url) or url
        page_id = url_identity_key(normalized)
        with self._lock:
            job = self._jobs[job_id]
            existing = job.pages.get(page_id, {})
            page = {
                "id": page_id,
                "job_id": job_id,
                "url": existing.get("url", url),
                "normalized_url": normalized,
                "title": title or existing.get("title"),
                "depth": min(depth, existing.get("depth", depth)),
                "selected": existing.get("selected", selected),
                "status": existing.get("status", status),
                "local_path": existing.get("local_path"),
                "http_status": existing.get("http_status"),
                "content_type": existing.get("content_type"),
                "size_bytes": existing.get("size_bytes"),
                "discovered_from_url": existing.get("discovered_from_url", discovered_from_url),
                "error_message": existing.get("error_message"),
                "created_at": existing.get("created_at", now_iso()),
                "updated_at": now_iso(),
            }
            job.pages[page_id] = page
            job.updated_at = time()
            return dict(page)

    def upsert_asset(
        self,
        job_id: str,
        url: str,
        asset_type: str,
        page_id: str | None,
        selected: bool | None = None,
        discovered_from_url: str | None = None,
        variant_group_id: str | None = None,
        variants: list[dict] | None = None,
    ) -> dict:
        normalized = normalize_url(url) or url
        asset_id = variant_group_id or url_identity_key(normalized)
        if selected is None:
            selected = True
        variant_records = variants or [{"url": normalized, "label": "original", "width": None}]
        occurrence_count = sum(variant.get("occurrence_count", 1) for variant in variant_records)
        with self._lock:
            job = self._jobs[job_id]
            existing = job.assets.get(asset_id, {})
            asset = {
                "id": asset_id,
                "job_id": job_id,
                "page_id": existing.get("page_id") or page_id,
                "url": existing.get("url", url),
                "normalized_url": normalized,
                "asset_type": asset_type,
                "selected": existing.get("selected", selected),
                "status": existing.get("status", "discovered"),
                "local_path": existing.get("local_path"),
                "http_status": existing.get("http_status"),
                "content_type": existing.get("content_type"),
                "size_bytes": existing.get("size_bytes"),
                "discovered_from_url": existing.get("discovered_from_url", discovered_from_url),
                "error_message": existing.get("error_message"),
                "variant_group_id": existing.get("variant_group_id", variant_group_id or asset_id),
                "variants": existing.get("variants", variant_records),
                "variant_count": existing.get("variant_count", len(variant_records)),
                "occurrence_count": existing.get("occurrence_count", occurrence_count),
                "selected_variant_url": existing.get("selected_variant_url", normalized),
                "created_at": existing.get("created_at", now_iso()),
                "updated_at": now_iso(),
            }
            job.assets[asset_id] = asset
            job.updated_at = time()
            return dict(asset)

    def set_asset_variant(self, job_id: str, asset_id: str, variant_url: str) -> None:
        normalized = normalize_url(variant_url) or variant_url
        with self._lock:
            asset = self._jobs[job_id].assets[asset_id]
            allowed_urls = {variant["url"] for variant in asset.get("variants", [])}
            if normalized not in allowed_urls:
                raise ValueError("variant URL is not part of this asset group")
            asset["url"] = normalized
            asset["normalized_url"] = normalized
            asset["selected_variant_url"] = normalized
            asset["updated_at"] = now_iso()
            self._jobs[job_id].updated_at = time()

    def update_page(self, job_id: str, page_id: str, **updates) -> None:
        with self._lock:
            page = self._jobs[job_id].pages[page_id]
            page.update(updates)
            page["updated_at"] = now_iso()
            self._jobs[job_id].updated_at = time()

    def update_asset(self, job_id: str, asset_id: str, **updates) -> None:
        with self._lock:
            asset = self._jobs[job_id].assets[asset_id]
            asset.update(updates)
            asset["updated_at"] = now_iso()
            self._jobs[job_id].updated_at = time()

    def set_page_selection(self, job_id: str, page_ids: list[str], selected: bool) -> None:
        with self._lock:
            for page_id in page_ids:
                if page_id in self._jobs[job_id].pages:
                    self._jobs[job_id].pages[page_id]["selected"] = selected
            self._jobs[job_id].updated_at = time()

    def set_asset_selection(self, job_id: str, asset_ids: list[str], selected: bool) -> None:
        with self._lock:
            for asset_id in asset_ids:
                if asset_id in self._jobs[job_id].assets:
                    self._jobs[job_id].assets[asset_id]["selected"] = selected
            self._jobs[job_id].updated_at = time()

    def set_output_root(self, job_id: str, output_root: str) -> None:
        with self._lock:
            self._jobs[job_id].output_root = output_root
            self._jobs[job_id].updated_at = time()

    def pause(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.paused = True
            job.status = "paused"
            job.updated_at = time()
        self.event(job_id, "info", "job_paused", "Job paused")

    def resume(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.paused = False
            if job.status == "paused":
                job.status = "ready"
            job.updated_at = time()
        self.event(job_id, "info", "job_resumed", "Job resumed")

    def cancel(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.cancelled = True
            job.status = "cancelled"
            job.updated_at = time()
        self.event(job_id, "warning", "job_cancelled", "Job cancelled")

    def is_paused(self, job_id: str) -> bool:
        with self._lock:
            return self._jobs[job_id].paused

    def is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            return self._jobs[job_id].cancelled

    def pages(self, job_id: str) -> list[dict]:
        with self._lock:
            return [dict(page) for page in self._jobs[job_id].pages.values()]

    def assets(self, job_id: str) -> list[dict]:
        with self._lock:
            return [dict(asset) for asset in self._jobs[job_id].assets.values()]

    def events(self, job_id: str, after_event_id: int | None = None) -> list[dict]:
        with self._lock:
            events = [dict(event) for event in self._jobs[job_id].events]
        if after_event_id is not None:
            events = [event for event in events if event["id"] > after_event_id]
        return events

    def failures(self, job_id: str) -> list[dict]:
        with self._lock:
            return [dict(failure) for failure in self._jobs[job_id].failures]

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
                "updated_at": job.updated_at,
                "source_url": job.source_url,
                "normalized_source_url": job.normalized_source_url,
                "settings": dict(job.settings),
                "output_root": job.output_root,
                "events": [dict(event) for event in job.events],
                "failures": [dict(failure) for failure in job.failures],
                "pages": [dict(page) for page in job.pages.values()],
                "assets": [dict(asset) for asset in job.assets.values()],
                "paused": job.paused,
                "cancelled": job.cancelled,
            }
