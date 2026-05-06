from page_scraper.api_contract import (
    api_asset,
    api_event,
    api_failure,
    api_job,
    api_page,
    error_response,
    map_job_status,
    success_response,
)


def test_success_response_wraps_data():
    assert success_response({"id": "job-1"}) == {"ok": True, "data": {"id": "job-1"}}


def test_error_response_wraps_error_details():
    assert error_response("invalid_request", "Bad input", {"field": "sourceUrl"}) == {
        "ok": False,
        "error": {
            "code": "invalid_request",
            "message": "Bad input",
            "details": {"field": "sourceUrl"},
        },
    }


def test_map_job_status_translates_legacy_statuses():
    assert map_job_status("done", job_type="scrape") == "completed"
    assert map_job_status("error", job_type="crawl") == "failed"
    assert map_job_status("running", job_type="crawl") == "discovering"
    assert map_job_status("running", job_type="scrape") == "downloading"


def test_api_job_uses_camel_case_and_summary_counts():
    job = api_job(
        {
            "id": "job-1",
            "type": "crawl",
            "status": "ready",
            "source_url": "https://example.com/start",
            "normalized_source_url": "https://example.com/start",
            "settings": {
                "max_depth": 2,
                "same_domain_only": True,
                "stay_under_start_path": True,
                "include_images": True,
            },
            "output_root": "data/jobs/example_job1",
            "created_at": 0.0,
            "updated_at": 0.0,
            "events": [],
            "failures": [{}],
            "pages": [{"selected": True}, {"selected": False}],
            "assets": [{"selected": True}],
            "paused": False,
            "cancelled": False,
        }
    )
    assert job["sourceUrl"] == "https://example.com/start"
    assert job["normalizedSourceUrl"] == "https://example.com/start"
    assert job["settings"] == {
        "maxDepth": 2,
        "sameDomainOnly": True,
        "stayUnderStartPath": True,
        "includeImages": True,
    }
    assert job["summary"] == {
        "pagesFound": 2,
        "pagesSelected": 1,
        "assetsFound": 1,
        "assetsSelected": 1,
        "failures": 1,
    }
    assert job["output"]["root"] == "data/jobs/example_job1"
    assert job["createdAt"] == "1970-01-01T00:00:00+00:00"
    assert job["updatedAt"] == "1970-01-01T00:00:00+00:00"


def test_api_page_uses_camel_case():
    page = api_page(
        {
            "id": "p1",
            "job_id": "job-1",
            "normalized_url": "https://example.com/a",
            "http_status": 200,
            "content_type": "text/html",
            "size_bytes": 10,
            "local_path": "pages/a/source.html",
            "discovered_from_url": None,
            "error_message": None,
        }
    )
    assert page["jobId"] == "job-1"
    assert page["normalizedUrl"] == "https://example.com/a"
    assert page["httpStatus"] == 200
    assert page["sizeBytes"] == 10


def test_api_asset_preserves_variant_data():
    asset = api_asset(
        {
            "id": "a1",
            "job_id": "job-1",
            "page_id": "p1",
            "asset_type": "image",
            "normalized_url": "https://example.com/i-540w.webp",
            "variant_group_id": "https://example.com/i.webp",
            "variant_count": 2,
            "occurrence_count": 4,
            "selected_variant_url": "https://example.com/i-540w.webp",
            "variants": [],
        }
    )
    assert asset["jobId"] == "job-1"
    assert asset["pageId"] == "p1"
    assert asset["assetType"] == "image"
    assert asset["variantGroupId"] == "https://example.com/i.webp"
    assert asset["variantCount"] == 2


def test_api_event_and_failure_use_camel_case():
    event = api_event({"job_id": "job-1", "event_type": "job_created", "created_at": "now"})
    failure = api_failure(
        {"job_id": "job-1", "related_type": "page", "failure_code": "fetch_failed", "created_at": "now"}
    )
    assert event["jobId"] == "job-1"
    assert event["eventType"] == "job_created"
    assert failure["relatedType"] == "page"
    assert failure["failureCode"] == "fetch_failed"
