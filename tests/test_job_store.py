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
