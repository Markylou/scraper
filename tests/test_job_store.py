from page_scraper.job_store import JobStore


def test_job_lifecycle():
    store = JobStore()
    job_id = store.create("scrape")

    store.log(job_id, "Starting")
    store.finish(job_id, {"ok": True})

    job = store.get(job_id)
    assert job["type"] == "scrape"
    assert job["status"] == "done"
    assert job["messages"] == ["Starting"]
    assert job["result"] == {"ok": True}


def test_structured_events_failures_and_controls():
    store = JobStore()
    job_id = store.create("crawl", status="created", source_url="https://example.com/start/")

    store.set_status(job_id, "discovering")
    event = store.event(job_id, "info", "page_discovered", "Found a page", {"url": "https://example.com/a/"})
    failure = store.failure(job_id, "page", "p1", "https://example.com/missing/", "http_404", "Not found")
    store.pause(job_id)
    assert store.is_paused(job_id)
    store.resume(job_id)
    assert not store.is_paused(job_id)
    store.cancel(job_id)
    assert store.is_cancelled(job_id)

    job = store.get(job_id)
    assert job["status"] == "cancelled"
    assert any(item["id"] == event["id"] for item in job["events"])
    assert job["failures"][0]["id"] == failure["id"]
    assert job["source_url"] == "https://example.com/start/"


def test_pages_assets_and_selection_are_tracked():
    store = JobStore()
    job_id = store.create("crawl", status="created")

    page = store.upsert_page(job_id, "https://example.com/a/", depth=1, discovered_from_url="https://example.com/")
    asset = store.upsert_asset(job_id, "https://example.com/image.png", "image", page["id"])
    store.set_page_selection(job_id, [page["id"]], False)
    store.set_asset_selection(job_id, [asset["id"]], False)

    assert store.pages(job_id)[0]["selected"] is False
    assert store.assets(job_id)[0]["selected"] is False
