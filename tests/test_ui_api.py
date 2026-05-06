from __future__ import annotations

from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from page_scraper import ui_server
from page_scraper.api_contract import error_response, success_response
from page_scraper.job_store import JobStore


def _with_server(callback):
    ui_server.JOBS = JobStore()
    server = ThreadingHTTPServer((ui_server.HOST, 0), ui_server.UIServerHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        callback(f"http://{ui_server.HOST}:{server.server_port}")
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def _request(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_health_contract_shape():
    response = success_response(
        {
            "server": "PageScraperUI/0.1",
            "apiVersion": "1",
            "capabilities": ["save-pages", "discover-pages"],
        }
    )
    assert response["ok"] is True
    assert response["data"]["apiVersion"] == "1"


def test_bad_request_contract_shape():
    response = error_response("invalid_request", "Enter a starting page link.")
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_request"


def test_health_route_returns_stable_envelope():
    def run(base_url: str):
        status, body = _request("GET", f"{base_url}/api/health")
        assert status == 200
        assert body["ok"] is True
        assert body["data"]["apiVersion"] == "1"
        assert "image-variant-selection" in body["data"]["capabilities"]

    _with_server(run)


def test_ping_route_returns_simple_server_status():
    def run(base_url: str):
        status, body = _request("GET", f"{base_url}/ping")
        assert status == 200
        assert body == {
            "ok": True,
            "data": {
                "status": "up",
                "service": "page-scraper",
                "apiVersion": "1",
            },
        }

    _with_server(run)


def test_create_job_returns_stable_data_and_compat_job_id():
    def run(base_url: str):
        status, body = _request(
            "POST",
            f"{base_url}/api/jobs",
            {
                "sourceUrl": "https://example.com/start/",
                "maxDepth": 1,
                "sameDomainOnly": True,
                "stayUnderStartPath": True,
                "includeImages": True,
                "includeDocuments": True,
            },
        )
        assert status == 202
        assert body["ok"] is True
        assert body["jobId"]
        assert body["data"]["id"] == body["jobId"]
        assert body["data"]["sourceUrl"] == "https://example.com/start/"

    _with_server(run)


def test_get_job_route_keeps_http_status_when_job_has_status_field():
    def run(base_url: str):
        job_id = ui_server.JOBS.create("crawl", status="ready", source_url="https://example.com/start/")

        status, body = _request("GET", f"{base_url}/api/jobs/{job_id}")

        assert status == 200
        assert body["ok"] is True
        assert body["data"]["id"] == job_id
        assert body["status"] == "ready"

    _with_server(run)


def test_unknown_job_route_returns_json_error():
    def run(base_url: str):
        status, body = _request("GET", f"{base_url}/api/jobs/undefined")

        assert status == 404
        assert body["ok"] is False
        assert body["error"]["code"] == "job_not_found"

    _with_server(run)


def test_unknown_job_action_does_not_start_background_worker():
    def run(base_url: str):
        status, body = _request("POST", f"{base_url}/api/jobs/undefined/discover")

        assert status == 404
        assert body["ok"] is False
        assert body["error"]["code"] == "job_not_found"

    _with_server(run)


def test_invalid_save_route_returns_error_envelope_and_rejected_compat_key():
    def run(base_url: str):
        status, body = _request("POST", f"{base_url}/api/jobs/save", {"urlsText": "not a url"})
        assert status == 400
        assert body["ok"] is False
        assert body["error"]["code"] == "invalid_urls"
        assert body["rejected"]

    _with_server(run)


def test_events_route_supports_after_event_id_query():
    def run(base_url: str):
        job_id = ui_server.JOBS.create("crawl", status="created")
        first = ui_server.JOBS.event(job_id, "info", "first", "First")
        second = ui_server.JOBS.event(job_id, "info", "second", "Second")

        status, body = _request("GET", f"{base_url}/api/jobs/{job_id}/events?afterEventId={first['id']}")
        assert status == 200
        assert body["ok"] is True
        assert body["data"] == [
            {
                "id": second["id"],
                "jobId": job_id,
                "level": "info",
                "eventType": "second",
                "message": "Second",
                "metadata": {},
                "createdAt": second["created_at"],
            }
        ]

    _with_server(run)


def test_manifest_route_returns_path_and_parsed_manifest():
    def run(base_url: str):
        output_root = Path("data/jobs/api-test-manifest")
        output_root.mkdir(parents=True, exist_ok=True)
        manifest_path = output_root / "manifest.json"
        if manifest_path.exists():
            manifest_path.unlink()

        job_id = ui_server.JOBS.create("crawl", status="completed", source_url="https://example.com/start/")
        ui_server.JOBS.set_output_root(job_id, str(output_root))

        status, body = _request("GET", f"{base_url}/api/jobs/{job_id}/manifest")
        assert status == 200
        assert body["ok"] is True
        assert body["data"]["path"].endswith("manifest.json")
        assert body["data"]["manifest"]["sourceUrl"] == "https://example.com/start/"
        assert body["manifest"].endswith("manifest.json")

    _with_server(run)


def test_add_urls_to_existing_job_adds_selected_pages():
    def run(base_url: str):
        job_id = ui_server.JOBS.create("crawl", status="ready", source_url="https://example.com/start/")
        status, body = _request(
            "POST",
            f"{base_url}/api/jobs/{job_id}/pages/add",
            {"urls": ["https://example.com/extra/"], "urlsText": "https://example.com/second/"},
        )
        assert status == 200
        assert body["ok"] is True
        assert body["meta"]["count"] == 2
        assert [page["url"] for page in body["data"]] == [
            "https://example.com/extra/",
            "https://example.com/second/",
        ]
        assert all(page["selected"] is True for page in body["data"])

    _with_server(run)


def test_open_folder_endpoint_allows_job_paths(monkeypatch=None):
    opened = []
    original = ui_server.open_local_folder
    ui_server.open_local_folder = lambda path: opened.append(path) or str(path)
    try:
        def run(base_url: str):
            output_root = Path("data/jobs/api-open-folder").resolve()
            output_root.mkdir(parents=True, exist_ok=True)
            status, body = _request("POST", f"{base_url}/api/system/open-folder", {"path": str(output_root)})
            assert status == 200
            assert body["ok"] is True
            assert opened == [str(output_root)]

        _with_server(run)
    finally:
        ui_server.open_local_folder = original


def test_open_folder_endpoint_rejects_non_job_paths():
    def run(base_url: str):
        status, body = _request("POST", f"{base_url}/api/system/open-folder", {"path": str(Path.cwd())})
        assert status == 400
        assert body["ok"] is False
        assert body["error"]["code"] == "invalid_path"

    _with_server(run)


def test_retry_failure_endpoint_accepts_recorded_failure():
    calls = []
    original = ui_server.retry_failure
    ui_server.retry_failure = lambda job_id, failure_id: calls.append((job_id, failure_id)) or {"ok": True}
    try:
        def run(base_url: str):
            job_id = ui_server.JOBS.create("crawl", status="completed_with_errors", source_url="https://example.com/start/")
            page = ui_server.JOBS.upsert_page(job_id, "https://example.com/missing/", 0, None, status="failed")
            failure = ui_server.JOBS.failure(job_id, "page", page["id"], page["url"], "network_error", "Nope")

            status, body = _request("POST", f"{base_url}/api/jobs/{job_id}/failures/{failure['id']}/retry")
            assert status == 202
            assert body["ok"] is True
            assert body["failureId"] == failure["id"]
            assert calls == [(job_id, failure["id"])]

        _with_server(run)
    finally:
        ui_server.retry_failure = original
