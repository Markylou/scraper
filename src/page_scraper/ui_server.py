from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from typing import Any
import webbrowser

from .content_builder import main as rebuild_page_content
from .core.crawler import DiscoverySettings, discover
from .core.downloader import download_selected
from .core.job_output import job_output_root
from .core.manifest import write_manifest
from .job_store import JobStore
from .paths import UI_DIR
from .scrape_service import scrape_urls
from .url_utils import normalize_pasted_urls


HOST = "127.0.0.1"
DEFAULT_PORT = 8765
JOBS = JobStore()


def run_job(job_id: str, target, *args) -> None:
    try:
        result = target(*args)
        JOBS.finish(job_id, result or {"ok": True})
    except Exception as exc:
        JOBS.fail(job_id, str(exc))


def run_scrape_job(job_id: str, urls: list[str], rejected: list[str]) -> None:
    def progress(message: str) -> None:
        JOBS.log(job_id, message)

    root = job_output_root(urls[0], job_id)
    pages_root = root / "pages"
    JOBS.set_output_root(job_id, str(root))
    JOBS.set_status(job_id, "downloading")
    JOBS.event(job_id, "info", "save_started", "Saving pasted pages", {"output_root": str(root)})

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


def run_build_job(builder) -> dict:
    return builder() or {"ok": True}


def run_discovery_job(job_id: str) -> None:
    try:
        result = discover(JOBS, job_id)
        job = JOBS.get(job_id)
        job_status = job["status"]
        JOBS.finish(job_id, result, status="done" if job_status == "ready" else job_status)
    except Exception as exc:
        JOBS.fail(job_id, str(exc))


def run_download_job(job_id: str) -> None:
    try:
        result = download_selected(JOBS, job_id)
        job = JOBS.get(job_id)
        job_status = job["status"]
        JOBS.finish(job_id, result, status="done" if job_status in {"completed", "completed_with_errors"} else job_status)
    except Exception as exc:
        JOBS.fail(job_id, str(exc))


class UIServerHandler(BaseHTTPRequestHandler):
    server_version = "PageScraperUI/0.1"

    def do_GET(self) -> None:
        if self.path == "/":
            self.send_file(UI_DIR / "index.html", "text/html; charset=utf-8")
            return
        if self.path == "/styles.css":
            self.send_file(UI_DIR / "styles.css", "text/css; charset=utf-8")
            return
        if self.path == "/app.js":
            self.send_file(UI_DIR / "app.js", "application/javascript; charset=utf-8")
            return
        if self.path == "/api/health":
            self.send_json(
                {
                    "ok": True,
                    "server": self.server_version,
                    "capabilities": [
                        "save-pages",
                        "refresh-content",
                        "discover-pages",
                        "download-selected",
                    ],
                }
            )
            return
        if self.path.startswith("/api/jobs/"):
            parts = self.path.strip("/").split("/")
            job_id = parts[2] if len(parts) >= 3 else ""
            if len(parts) == 3:
                self.send_json(JOBS.get(job_id))
                return
            if len(parts) == 4 and parts[3] == "pages":
                self.send_json({"pages": JOBS.pages(job_id)})
                return
            if len(parts) == 4 and parts[3] == "assets":
                self.send_json({"assets": JOBS.assets(job_id)})
                return
            if len(parts) == 4 and parts[3] == "events":
                self.send_json({"events": JOBS.events(job_id)})
                return
            if len(parts) == 4 and parts[3] == "failures":
                self.send_json({"failures": JOBS.failures(job_id)})
                return
            if len(parts) == 4 and parts[3] == "manifest":
                manifest_path = write_manifest(JOBS, job_id)
                self.send_json({"manifest": str(manifest_path), "path": str(manifest_path)})
                return
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path == "/api/scrape":
            payload = self.read_json()
            urls_text = str(payload.get("urlsText", ""))
            urls, rejected = normalize_pasted_urls(urls_text)
            if not urls:
                self.send_json(
                    {"error": "Paste at least one usable page link.", "rejected": rejected},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            job_id = JOBS.create(
                "scrape",
                source_url=urls[0],
                settings={"mode": "save_pages", "url_count": len(urls)},
            )
            thread = Thread(target=run_scrape_job, args=(job_id, urls, rejected), daemon=True)
            thread.start()
            self.send_json({"jobId": job_id, "rejected": rejected}, status=HTTPStatus.ACCEPTED)
            return

        if self.path == "/api/build/page-content":
            self.start_background_job("build-page-content", rebuild_page_content)
            return

        if self.path == "/api/jobs":
            payload = self.read_json()
            source_url = str(payload.get("sourceUrl", "")).strip()
            if not source_url:
                self.send_json({"error": "Enter a starting page link."}, status=HTTPStatus.BAD_REQUEST)
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
            self.send_json({"jobId": job_id, "job": JOBS.get(job_id)}, status=HTTPStatus.ACCEPTED)
            return

        if self.path.startswith("/api/jobs/"):
            parts = self.path.strip("/").split("/")
            job_id = parts[2] if len(parts) >= 3 else ""
            action = parts[3] if len(parts) >= 4 else ""
            if action == "discover":
                thread = Thread(target=run_discovery_job, args=(job_id,), daemon=True)
                thread.start()
                self.send_json({"jobId": job_id}, status=HTTPStatus.ACCEPTED)
                return
            if action == "download":
                thread = Thread(target=run_download_job, args=(job_id,), daemon=True)
                thread.start()
                self.send_json({"jobId": job_id}, status=HTTPStatus.ACCEPTED)
                return
            if action == "pause":
                JOBS.pause(job_id)
                self.send_json({"job": JOBS.get(job_id)})
                return
            if action == "resume":
                JOBS.resume(job_id)
                self.send_json({"job": JOBS.get(job_id)})
                return
            if action == "cancel":
                JOBS.cancel(job_id)
                self.send_json({"job": JOBS.get(job_id)})
                return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_PATCH(self) -> None:
        if self.path.startswith("/api/jobs/"):
            payload = self.read_json()
            parts = self.path.strip("/").split("/")
            job_id = parts[2] if len(parts) >= 3 else ""
            if len(parts) == 5 and parts[3] == "pages" and parts[4] == "selection":
                JOBS.set_page_selection(job_id, list(payload.get("ids", [])), bool(payload.get("selected", True)))
                self.send_json({"pages": JOBS.pages(job_id)})
                return
            if len(parts) == 5 and parts[3] == "assets" and parts[4] == "selection":
                JOBS.set_asset_selection(job_id, list(payload.get("ids", [])), bool(payload.get("selected", True)))
                self.send_json({"assets": JOBS.assets(job_id)})
                return
        self.send_error(HTTPStatus.NOT_FOUND)

    def start_background_job(self, job_type: str, target) -> None:
        job_id = JOBS.create(job_type)
        thread = Thread(target=run_job, args=(job_id, run_build_job, target), daemon=True)
        thread.start()
        self.send_json({"jobId": job_id}, status=HTTPStatus.ACCEPTED)

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

    def log_message(self, format: str, *args) -> None:
        return


def serve(port: int = DEFAULT_PORT, open_browser: bool = True) -> None:
    url = f"http://{HOST}:{port}"
    server = ThreadingHTTPServer((HOST, port), UIServerHandler)
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
