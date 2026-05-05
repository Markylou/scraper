from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from typing import Any
import webbrowser

from .content_builder import main as rebuild_page_content
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

    outcomes = scrape_urls(urls, progress=progress)
    JOBS.finish(
        job_id,
        {
            "ok": all(outcome.ok for outcome in outcomes),
            "saved": [outcome.to_dict() for outcome in outcomes],
            "rejected": rejected,
        },
    )


def run_build_job(builder) -> dict:
    return builder() or {"ok": True}


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
        if self.path.startswith("/api/jobs/"):
            job_id = self.path.removeprefix("/api/jobs/").strip("/")
            self.send_json(JOBS.get(job_id))
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

            job_id = JOBS.create("scrape")
            thread = Thread(target=run_scrape_job, args=(job_id, urls, rejected), daemon=True)
            thread.start()
            self.send_json({"jobId": job_id, "rejected": rejected}, status=HTTPStatus.ACCEPTED)
            return

        if self.path == "/api/build/page-content":
            self.start_background_job("build-page-content", rebuild_page_content)
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
