from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from threading import Thread
from typing import Any
from urllib.parse import parse_qs, urlparse
import webbrowser

from .api_contract import (
    api_asset,
    api_event,
    api_failure,
    api_job,
    api_page,
    error_response,
    success_response,
)
from .content_builder import main as rebuild_page_content
from .core.crawler import DiscoverySettings, discover
from .core.downloader import download_selected
from .core.job_output import job_output_root
from .core.manifest import write_manifest
from .job_store import JobStore
from .logging_config import configure_logging, get_logger
from .paths import JOBS_DIR, UI_DIR
from .scrape_service import scrape_urls
from .url_utils import normalize_pasted_urls


HOST = "127.0.0.1"
DEFAULT_PORT = 8765
JOBS = JobStore()
LOGGER = get_logger("ui_server")


def run_job(job_id: str, target, *args) -> None:
    LOGGER.info("Background job started job_id=%s target=%s", job_id, getattr(target, "__name__", str(target)))
    try:
        result = target(*args)
        JOBS.finish(job_id, result or {"ok": True})
        LOGGER.info("Background job finished job_id=%s", job_id)
    except Exception as exc:
        LOGGER.exception("Background job failed job_id=%s", job_id)
        JOBS.fail(job_id, str(exc))


def run_scrape_job(job_id: str, urls: list[str], rejected: list[str]) -> None:
    def progress(message: str) -> None:
        JOBS.log(job_id, message)

    root = job_output_root(urls[0], job_id)
    pages_root = root / "pages"
    JOBS.set_output_root(job_id, str(root))
    JOBS.set_status(job_id, "downloading")
    JOBS.event(job_id, "info", "save_started", "Saving pasted pages", {"output_root": str(root)})
    LOGGER.info("Save pages started job_id=%s urls=%s rejected=%s output_root=%s", job_id, len(urls), len(rejected), root)

    outcomes = scrape_urls(
        urls,
        progress=progress,
        pages_dir=pages_root,
        display_root=f"data/jobs/{root.name}/pages",
    )
    for outcome in outcomes:
        if outcome.ok and outcome.saved_folder:
            page = JOBS.upsert_page(job_id, outcome.url, 0, None, title=outcome.url, status="downloaded")
            source_file = pages_root / outcome.saved_folder / "source.html"
            JOBS.update_page(
                job_id,
                page["id"],
                local_path=f"pages/{outcome.saved_folder}/source.html",
                size_bytes=source_file.stat().st_size if source_file.exists() else None,
            )
        else:
            LOGGER.warning("Save page failed job_id=%s url=%s message=%s", job_id, outcome.url, outcome.message)
            JOBS.failure(job_id, "page", None, outcome.url, "save_failed", outcome.message)

    failed_count = len([outcome for outcome in outcomes if not outcome.ok])
    status = "completed_with_errors" if failed_count or rejected else "completed"
    JOBS.set_status(job_id, status)
    write_manifest(JOBS, job_id)
    JOBS.finish(
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
    LOGGER.info("Save pages finished job_id=%s status=%s failed=%s rejected=%s", job_id, status, failed_count, len(rejected))


def run_build_job(builder) -> dict:
    return builder() or {"ok": True}


def run_discovery_job(job_id: str) -> None:
    try:
        LOGGER.info("Discovery job requested job_id=%s", job_id)
        result = discover(JOBS, job_id)
        job = JOBS.get(job_id)
        job_status = job["status"]
        JOBS.finish(job_id, result, status="done" if job_status == "ready" else job_status)
    except Exception as exc:
        LOGGER.exception("Discovery job failed job_id=%s", job_id)
        JOBS.fail(job_id, str(exc))


def run_download_job(job_id: str) -> None:
    try:
        LOGGER.info("Download job requested job_id=%s", job_id)
        result = download_selected(JOBS, job_id)
        job = JOBS.get(job_id)
        job_status = job["status"]
        JOBS.finish(job_id, result, status="done" if job_status in {"completed", "completed_with_errors"} else job_status)
    except Exception as exc:
        LOGGER.exception("Download job failed job_id=%s", job_id)
        JOBS.fail(job_id, str(exc))


def retry_failure(job_id: str, failure_id: str) -> dict:
    failure = next((item for item in JOBS.failures(job_id) if item["id"] == failure_id), None)
    if not failure:
        raise ValueError("Failure was not found.")

    related_type = failure.get("related_type")
    related_id = failure.get("related_id")
    url = failure.get("url")
    if related_type == "page":
        page = next((item for item in JOBS.pages(job_id) if item["id"] == related_id), None)
        if page is None and url:
            page = JOBS.upsert_page(job_id, url, 0, None, status="discovered")
        if page is None:
            raise ValueError("Could not find the page to retry.")
        JOBS.update_page(job_id, page["id"], status="discovered", error_message=None)
        JOBS.set_page_selection(job_id, [page["id"]], True)
        return {"related_type": "page", "related_id": page["id"]}

    if related_type == "asset":
        asset = next((item for item in JOBS.assets(job_id) if item["id"] == related_id), None)
        if asset is None:
            raise ValueError("Could not find the file to retry.")
        JOBS.update_asset(job_id, asset["id"], status="discovered", error_message=None)
        JOBS.set_asset_selection(job_id, [asset["id"]], True)
        return {"related_type": "asset", "related_id": asset["id"]}

    raise ValueError("This failure type cannot be retried.")


def run_retry_failure_job(job_id: str, retry: dict) -> None:
    try:
        LOGGER.info("Retry failure job started job_id=%s retry=%s", job_id, retry)
        related_type = retry["related_type"]
        related_id = retry["related_id"]

        page_selection = {page["id"]: page.get("selected", True) for page in JOBS.pages(job_id)}
        asset_selection = {asset["id"]: asset.get("selected", False) for asset in JOBS.assets(job_id)}
        if page_selection:
            JOBS.set_page_selection(job_id, list(page_selection), False)
        if asset_selection:
            JOBS.set_asset_selection(job_id, list(asset_selection), False)
        if related_type == "page":
            JOBS.set_page_selection(job_id, [related_id], True)
        if related_type == "asset":
            JOBS.set_asset_selection(job_id, [related_id], True)

        result = download_selected(JOBS, job_id)

        for page_id, selected in page_selection.items():
            JOBS.set_page_selection(job_id, [page_id], selected)
        for asset_id, selected in asset_selection.items():
            JOBS.set_asset_selection(job_id, [asset_id], selected)
        JOBS.finish(job_id, result, status="done" if JOBS.get(job_id)["status"] in {"completed", "completed_with_errors"} else JOBS.get(job_id)["status"])
        LOGGER.info("Retry failure job finished job_id=%s retry=%s", job_id, retry)
    except Exception as exc:
        LOGGER.exception("Retry failure job failed job_id=%s retry=%s", job_id, retry)
        JOBS.fail(job_id, str(exc))


def open_local_folder(path: str) -> str:
    target = Path(path).expanduser().resolve()
    if target.is_file():
        target = target.parent
    jobs_root = JOBS_DIR.resolve()
    if target != jobs_root and jobs_root not in target.parents:
        LOGGER.warning("Open folder rejected path=%s", target)
        raise ValueError("Only job output folders can be opened.")
    if not target.exists() or not target.is_dir():
        LOGGER.warning("Open folder missing path=%s", target)
        raise ValueError("Folder was not found.")
    os.startfile(str(target))
    LOGGER.info("Open folder requested path=%s", target)
    return str(target)


class UIServerHandler(BaseHTTPRequestHandler):
    server_version = "PageScraperUI/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            self.send_file(UI_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path == "/styles.css":
            self.send_file(UI_DIR / "styles.css", "text/css; charset=utf-8")
            return
        if path == "/app.js":
            self.send_file(UI_DIR / "app.js", "application/javascript; charset=utf-8")
            return
        if path == "/ping":
            self.send_api_data(
                {
                    "status": "up",
                    "service": "page-scraper",
                    "apiVersion": "1",
                }
            )
            return
        if path == "/api/health":
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
            return
        if path.startswith("/api/jobs/"):
            parts = path.strip("/").split("/")
            job_id = parts[2] if len(parts) >= 3 else ""
            if not self.send_job_not_found_if_missing(job_id):
                return
            if len(parts) == 3:
                job = JOBS.get(job_id)
                self.send_api_data(api_job(job), **job)
                return
            if len(parts) == 4 and parts[3] == "pages":
                pages = JOBS.pages(job_id)
                api_pages = [api_page(page) for page in pages]
                self.send_api_data(api_pages, meta={"count": len(api_pages)}, pages=pages)
                return
            if len(parts) == 4 and parts[3] == "assets":
                assets = JOBS.assets(job_id)
                api_assets = [api_asset(asset) for asset in assets]
                self.send_api_data(api_assets, meta={"count": len(api_assets)}, assets=assets)
                return
            if len(parts) == 4 and parts[3] == "events":
                after_event_id = None
                if query.get("afterEventId"):
                    after_event_id = int(query["afterEventId"][0])
                events = JOBS.events(job_id, after_event_id=after_event_id)
                api_events = [api_event(event) for event in events]
                self.send_api_data(api_events, meta={"count": len(api_events)}, events=events)
                return
            if len(parts) == 4 and parts[3] == "failures":
                failures = JOBS.failures(job_id)
                api_failures = [api_failure(failure) for failure in failures]
                self.send_api_data(api_failures, meta={"count": len(api_failures)}, failures=failures)
                return
            if len(parts) == 4 and parts[3] == "manifest":
                manifest_path = write_manifest(JOBS, job_id)
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                self.send_api_data(
                    {"path": str(manifest_path), "manifest": manifest},
                    manifest=str(manifest_path),
                    path=str(manifest_path),
                )
                return
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/scrape":
            payload = self.read_json()
            self.start_save_pages_job(str(payload.get("urlsText", "")))
            return

        if path == "/api/build/page-content":
            self.start_background_job("build-page-content", rebuild_page_content)
            return

        if path == "/api/jobs/save":
            payload = self.read_json()
            self.start_save_pages_job(str(payload.get("urlsText", "")), urls_list=list(payload.get("urls", [])))
            return

        if path == "/api/system/open-folder":
            payload = self.read_json()
            try:
                opened_path = open_local_folder(str(payload.get("path", "")))
            except Exception as exc:
                LOGGER.warning("Open folder request failed error=%s", exc)
                self.send_api_error("invalid_path", str(exc), status=HTTPStatus.BAD_REQUEST)
                return
            self.send_api_data({"path": opened_path})
            return

        if path == "/api/jobs":
            payload = self.read_json()
            source_url = str(payload.get("sourceUrl", "")).strip()
            if not source_url:
                self.send_api_error(
                    "invalid_request",
                    "Enter a starting page link.",
                    status=HTTPStatus.BAD_REQUEST,
                    userMessage="Enter a starting page link.",
                )
                return
            settings = DiscoverySettings(
                max_depth=int(payload.get("maxDepth", 2)),
                same_domain_only=bool(payload.get("sameDomainOnly", True)),
                stay_under_start_path=bool(payload.get("stayUnderStartPath", True)),
                include_images=bool(payload.get("includeImages", True)),
                include_documents=bool(payload.get("includeDocuments", True)),
                include_video=bool(payload.get("includeVideo", False)),
            ).to_dict()
            job_id = JOBS.create("crawl", status="created", source_url=source_url, settings=settings)
            job = JOBS.get(job_id)
            self.send_api_data(api_job(job), http_status=HTTPStatus.ACCEPTED, jobId=job_id, job=job)
            return

        if path.startswith("/api/jobs/"):
            parts = path.strip("/").split("/")
            job_id = parts[2] if len(parts) >= 3 else ""
            action = parts[3] if len(parts) >= 4 else ""
            if not self.send_job_not_found_if_missing(job_id):
                return
            if len(parts) == 5 and parts[3] == "pages" and parts[4] == "add":
                payload = self.read_json()
                urls_text = str(payload.get("urlsText", ""))
                url_list = list(payload.get("urls", []))
                combined_text = urls_text
                if url_list:
                    combined_text = "\n".join([*[str(url) for url in url_list if str(url).strip()], combined_text])
                urls, rejected = normalize_pasted_urls(combined_text)
                if not urls:
                    self.send_api_error(
                        "invalid_urls",
                        "Add at least one usable page link.",
                        status=HTTPStatus.BAD_REQUEST,
                        details={"rejected": rejected},
                        rejected=rejected,
                    )
                    return
                added = []
                for url in urls:
                    added.append(JOBS.upsert_page(job_id, url, 0, None, title=url, status="discovered", selected=True))
                api_pages = [api_page(page) for page in added]
                self.send_api_data(api_pages, meta={"count": len(api_pages)}, pages=added, rejected=rejected)
                return
            if action == "discover":
                thread = Thread(target=run_discovery_job, args=(job_id,), daemon=True)
                thread.start()
                self.send_api_data({"jobId": job_id}, http_status=HTTPStatus.ACCEPTED, jobId=job_id)
                return
            if action == "download":
                thread = Thread(target=run_download_job, args=(job_id,), daemon=True)
                thread.start()
                self.send_api_data({"jobId": job_id}, http_status=HTTPStatus.ACCEPTED, jobId=job_id)
                return
            if action == "pause":
                JOBS.pause(job_id)
                job = JOBS.get(job_id)
                self.send_api_data(api_job(job), job=job)
                return
            if action == "resume":
                JOBS.resume(job_id)
                job = JOBS.get(job_id)
                self.send_api_data(api_job(job), job=job)
                return
            if action == "cancel":
                JOBS.cancel(job_id)
                job = JOBS.get(job_id)
                self.send_api_data(api_job(job), job=job)
                return
            if len(parts) == 6 and parts[3] == "failures" and parts[5] == "retry":
                failure_id = parts[4]
                try:
                    retry = retry_failure(job_id, failure_id)
                except Exception as exc:
                    LOGGER.warning("Retry request failed job_id=%s failure_id=%s error=%s", job_id, failure_id, exc)
                    self.send_api_error("retry_failed", str(exc), status=HTTPStatus.BAD_REQUEST)
                    return
                thread = Thread(target=run_retry_failure_job, args=(job_id, retry), daemon=True)
                thread.start()
                self.send_api_data({"jobId": job_id, "failureId": failure_id}, http_status=HTTPStatus.ACCEPTED, jobId=job_id, failureId=failure_id)
                return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/jobs/"):
            payload = self.read_json()
            parts = path.strip("/").split("/")
            job_id = parts[2] if len(parts) >= 3 else ""
            if not self.send_job_not_found_if_missing(job_id):
                return
            if len(parts) == 5 and parts[3] == "pages" and parts[4] == "selection":
                JOBS.set_page_selection(job_id, list(payload.get("ids", [])), bool(payload.get("selected", True)))
                pages = JOBS.pages(job_id)
                self.send_api_data([api_page(page) for page in pages], meta={"count": len(pages)}, pages=pages)
                return
            if len(parts) == 5 and parts[3] == "assets" and parts[4] == "selection":
                JOBS.set_asset_selection(job_id, list(payload.get("ids", [])), bool(payload.get("selected", True)))
                assets = JOBS.assets(job_id)
                self.send_api_data([api_asset(asset) for asset in assets], meta={"count": len(assets)}, assets=assets)
                return
            if len(parts) == 5 and parts[3] == "assets" and parts[4] == "variant":
                JOBS.set_asset_variant(job_id, str(payload.get("assetId", "")), str(payload.get("url", "")))
                assets = JOBS.assets(job_id)
                self.send_api_data([api_asset(asset) for asset in assets], meta={"count": len(assets)}, assets=assets)
                return
        self.send_error(HTTPStatus.NOT_FOUND)

    def start_background_job(self, job_type: str, target) -> None:
        job_id = JOBS.create(job_type)
        thread = Thread(target=run_job, args=(job_id, run_build_job, target), daemon=True)
        thread.start()
        self.send_api_data({"jobId": job_id}, http_status=HTTPStatus.ACCEPTED, jobId=job_id)

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
                userMessage="Paste at least one usable page link.",
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
        self.send_api_data({"jobId": job_id}, http_status=HTTPStatus.ACCEPTED, jobId=job_id, rejected=rejected)

    def send_job_not_found_if_missing(self, job_id: str) -> bool:
        if job_id and JOBS.exists(job_id):
            return True
        LOGGER.warning("Job route rejected missing job_id=%s path=%s", job_id, self.path)
        self.send_api_error(
            "job_not_found",
            "That job is no longer available. Start a new one and try again.",
            status=HTTPStatus.NOT_FOUND,
            userMessage="That job is no longer available. Start a new one and try again.",
        )
        return False

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_api_data(
        self,
        data: Any,
        http_status: HTTPStatus = HTTPStatus.OK,
        meta: dict | None = None,
        **compat,
    ) -> None:
        payload = success_response(data, meta=meta)
        payload.update(compat)
        self.send_json(payload, status=http_status)

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

    def log_message(self, format: str, *args) -> None:
        return


def serve(port: int = DEFAULT_PORT, open_browser: bool = True) -> None:
    configure_logging()
    url = f"http://{HOST}:{port}"
    server = ThreadingHTTPServer((HOST, port), UIServerHandler)
    LOGGER.info("Page Saver starting url=%s open_browser=%s", url, open_browser)
    print(f"Page Saver is running at {url}")
    if open_browser:
        webbrowser.open(url)
    server.serve_forever()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Launch the local page-scraper UI.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    serve(port=args.port, open_browser=not args.no_browser)
