from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from page_scraper.api.app import app
from page_scraper.api.dependencies import get_job_store
from page_scraper.job_store import JobStore


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_job_store():
    """Reset the global job store between tests so they are isolated."""
    store = get_job_store()
    store._jobs.clear()  # type: ignore[attr-defined]
    yield


def test_health_contract_shape():
    response = {
        "ok": True,
        "data": {
            "server": "PageScraperUI/0.1",
            "apiVersion": "1",
            "capabilities": ["save-pages", "discover-pages"],
        },
    }
    assert response["ok"] is True
    assert response["data"]["apiVersion"] == "1"


def test_bad_request_contract_shape():
    response = {
        "ok": False,
        "error": {
            "code": "invalid_request",
            "message": "Enter a starting page link.",
            "details": {},
        },
    }
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_request"


def test_health_route_returns_stable_envelope():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["apiVersion"] == "1"
    assert "image-variant-selection" in body["data"]["capabilities"]


def test_ping_route_returns_simple_server_status():
    resp = client.get("/ping")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "ok": True,
        "data": {
            "status": "up",
            "service": "page-scraper",
            "apiVersion": "1",
        },
    }


def test_create_job_returns_stable_data_and_compat_job_id():
    resp = client.post(
        "/api/jobs",
        json={
            "sourceUrl": "https://example.com/start/",
            "maxDepth": 1,
            "sameDomainOnly": True,
            "stayUnderStartPath": True,
            "includeImages": True,
            "includeDocuments": True,
        },
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["ok"] is True
    assert body["jobId"]
    assert body["data"]["id"] == body["jobId"]
    assert body["data"]["sourceUrl"] == "https://example.com/start/"


def test_get_job_route_keeps_http_status_when_job_has_status_field():
    # Create a job first
    create = client.post("/api/jobs", json={"sourceUrl": "https://example.com/start/"})
    job_id = create.json()["jobId"]

    resp = client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["id"] == job_id
    assert body["status"] == "created"


def test_unknown_job_route_returns_json_error():
    resp = client.get("/api/jobs/undefined")
    assert resp.status_code == 404
    body = resp.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "job_not_found"


def test_unknown_job_action_does_not_start_background_worker():
    resp = client.post("/api/jobs/undefined/discover")
    assert resp.status_code == 404
    body = resp.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "job_not_found"


def test_invalid_save_route_returns_error_envelope_and_rejected_compat_key():
    resp = client.post("/api/jobs/save", json={"urlsText": "not a url"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "invalid_urls"
    assert "rejected" in body


def test_events_route_supports_after_event_id_query():
    # Create job and add some events
    create = client.post("/api/jobs", json={"sourceUrl": "https://example.com/start/"})
    job_id = create.json()["jobId"]

    store = get_job_store()
    first = store.event(job_id, "info", "first", "First")
    second = store.event(job_id, "info", "second", "Second")

    resp = client.get(f"/api/jobs/{job_id}/events?afterEventId={first['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["message"] == "Second"


def test_manifest_route_returns_path_and_parsed_manifest(tmp_path):
    # Create a completed job with output
    create = client.post("/api/jobs", json={"sourceUrl": "https://example.com/start/"})
    job_id = create.json()["jobId"]

    store = get_job_store()
    output_root = tmp_path / "example_manifest_test"
    output_root.mkdir(parents=True, exist_ok=True)
    store.set_output_root(job_id, str(output_root))

    # Write a fake manifest so the endpoint has something to read
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps({"sourceUrl": "https://example.com/start/"}), encoding="utf-8")

    resp = client.get(f"/api/jobs/{job_id}/manifest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["path"].endswith("manifest.json")
    assert body["data"]["manifest"]["sourceUrl"] == "https://example.com/start/"


def test_add_urls_to_existing_job_adds_selected_pages():
    create = client.post("/api/jobs", json={"sourceUrl": "https://example.com/start/"})
    job_id = create.json()["jobId"]

    resp = client.post(
        f"/api/jobs/{job_id}/pages/add",
        json={
            "urls": ["https://example.com/extra/"],
            "urlsText": "https://example.com/second/",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["meta"]["count"] == 2
    urls = [p["url"] for p in body["data"]]
    assert "https://example.com/extra/" in urls
    assert "https://example.com/second/" in urls
    assert all(p["selected"] is True for p in body["data"])


def test_open_folder_endpoint_rejects_non_job_paths():
    resp = client.post("/api/system/open-folder", json={"path": str(Path.cwd())})
    assert resp.status_code == 400
    body = resp.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "invalid_path"


def test_retry_failure_endpoint_accepts_recorded_failure():
    create = client.post("/api/jobs", json={"sourceUrl": "https://example.com/start/"})
    job_id = create.json()["jobId"]

    store = get_job_store()
    page = store.upsert_page(job_id, "https://example.com/missing/", 0, None, status="failed")
    failure = store.failure(job_id, "page", page["id"], page["url"], "network_error", "Nope")

    resp = client.post(f"/api/jobs/{job_id}/failures/{failure['id']}/retry")
    assert resp.status_code == 202
    body = resp.json()
    assert body["ok"] is True
    assert body["failureId"] == failure["id"]