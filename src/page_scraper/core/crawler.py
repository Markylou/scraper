from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from typing import Callable

from bs4 import BeautifulSoup

from ..fetch_playwright import fetch_page_html
from ..fetch_requests import fetch_url, html_needs_browser
from ..logging_config import get_logger
from ..page_archive import title_from_html
from .asset_discovery import discover_assets
from .normalizer import normalize_url, same_domain, under_start_path, url_identity_key


LOGGER = get_logger("crawler")


@dataclass(frozen=True)
class DiscoverySettings:
    max_depth: int = 2
    same_domain_only: bool = True
    stay_under_start_path: bool = True
    include_html: bool = True
    include_images: bool = True
    include_documents: bool = True
    include_video: bool = False
    use_playwright_fallback: bool = True

    @classmethod
    def from_dict(cls, value: dict | None) -> "DiscoverySettings":
        if not value:
            return cls()
        allowed = {field: value[field] for field in cls.__dataclass_fields__ if field in value}
        if "max_depth" in allowed:
            allowed["max_depth"] = int(allowed["max_depth"])
        return cls(**allowed)

    def to_dict(self) -> dict:
        return asdict(self)


def default_fetch_html(url: str, settings: DiscoverySettings) -> str:
    result = fetch_url(url)
    html = result.text or ""
    if settings.use_playwright_fallback and html_needs_browser(html):
        import asyncio

        _, html = asyncio.run(fetch_page_html(url))
    return html


def extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for element in soup.select("a[href]"):
        normalized = normalize_url(element.get("href") or "", base_url)
        if normalized:
            links.append(normalized)
    return links


def asset_allowed(asset: dict, settings: DiscoverySettings) -> bool:
    asset_type = asset["asset_type"]
    if asset_type == "image":
        return settings.include_images
    if asset_type == "document":
        return settings.include_documents
    if asset_type == "video":
        return settings.include_video
    return False


def discover(
    store,
    job_id: str,
    fetch_html: Callable[[str], str] | None = None,
) -> dict:
    job = store.get(job_id)
    settings = DiscoverySettings.from_dict(job.get("settings"))
    start_url = normalize_url(job["source_url"])
    if not start_url:
        store.failure(job_id, "job", job_id, job.get("source_url"), "invalid_url", "Start URL is not usable")
        store.set_status(job_id, "failed")
        return {"ok": False, "pages_discovered": 0, "assets_discovered": 0}

    fetcher = fetch_html or (lambda url: default_fetch_html(url, settings))
    store.set_status(job_id, "discovering")
    store.event(job_id, "info", "discovery_started", "Finding pages", {"source_url": start_url})
    LOGGER.info(
        "Discovery started job_id=%s source_url=%s max_depth=%s same_domain_only=%s stay_under_start_path=%s",
        job_id,
        start_url,
        settings.max_depth,
        settings.same_domain_only,
        settings.stay_under_start_path,
    )

    queue = deque([(start_url, 0, None)])
    seen: set[str] = set()

    while queue:
        if store.is_cancelled(job_id):
            break

        url, depth, parent_url = queue.popleft()
        normalized = normalize_url(url)
        if not normalized:
            store.failure(job_id, "page", None, url, "invalid_url", "URL is not usable")
            continue

        identity = url_identity_key(normalized)
        if identity in seen:
            continue
        seen.add(identity)

        if settings.same_domain_only and not same_domain(normalized, start_url):
            store.failure(job_id, "page", None, normalized, "skipped_external_domain", "Skipped external page")
            continue
        if settings.stay_under_start_path and not under_start_path(normalized, start_url):
            store.failure(job_id, "page", None, normalized, "skipped_outside_start_path", "Skipped page outside start path")
            continue

        try:
            html = fetcher(normalized)
        except Exception as exc:
            LOGGER.exception("Discovery fetch failed job_id=%s url=%s", job_id, normalized)
            store.failure(job_id, "page", None, normalized, "network_error", str(exc))
            continue

        page = store.upsert_page(
            job_id,
            normalized,
            depth=depth,
            discovered_from_url=parent_url,
            title=title_from_html(html, normalized),
        )
        store.event(job_id, "info", "page_discovered", "Found page", {"url": normalized, "depth": depth})

        for asset in discover_assets(html, normalized):
            if not asset_allowed(asset, settings):
                continue
            stored = store.upsert_asset(
                job_id,
                asset["url"],
                asset["asset_type"],
                page["id"],
                selected=asset["selected"],
                discovered_from_url=normalized,
                variant_group_id=asset.get("variant_group_id"),
                variants=asset.get("variants"),
            )
            store.event(job_id, "info", "asset_discovered", "Found file", {"url": stored["url"], "type": stored["asset_type"]})

        if depth >= settings.max_depth:
            continue
        for link in extract_links(html, normalized):
            queue.append((link, depth + 1, normalized))

    failures = store.failures(job_id)
    status = "ready" if not store.is_cancelled(job_id) else "cancelled"
    store.set_status(job_id, status)
    store.event(job_id, "info", "discovery_completed", "Finished finding pages")
    LOGGER.info(
        "Discovery finished job_id=%s status=%s pages=%s assets=%s failures=%s",
        job_id,
        status,
        len(store.pages(job_id)),
        len(store.assets(job_id)),
        len(failures),
    )
    return {
        "ok": status == "ready",
        "pages_discovered": len(store.pages(job_id)),
        "assets_discovered": len(store.assets(job_id)),
        "failures": len(failures),
    }
