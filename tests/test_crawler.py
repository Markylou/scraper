from page_scraper.core.crawler import DiscoverySettings, discover
from page_scraper.job_store import JobStore


def test_discover_applies_depth_boundaries_and_records_assets():
    pages = {
        "https://example.com/games/start/": """
            <main>
              <a href="chapter-1/">Chapter</a>
              <a href="https://example.com/other/">Outside path</a>
              <a href="https://elsewhere.com/page/">External</a>
              <img src="/images/logo.png">
            </main>
        """,
        "https://example.com/games/start/chapter-1/": """
            <main>
              <a href="deep/">Too deep</a>
              <a href="../start/">Duplicate start</a>
              <a href="/docs/map.pdf">Map</a>
            </main>
        """,
    }

    def fetch(url):
        return pages[url]

    store = JobStore()
    job_id = store.create(
        "crawl",
        status="created",
        source_url="https://example.com/games/start/",
        settings=DiscoverySettings(max_depth=1).to_dict(),
    )

    summary = discover(store, job_id, fetch_html=fetch)

    assert summary["pages_discovered"] == 2
    assert summary["assets_discovered"] == 2
    assert [page["url"] for page in store.pages(job_id)] == [
        "https://example.com/games/start/",
        "https://example.com/games/start/chapter-1/",
    ]
    assert any(failure["failure_code"] == "skipped_external_domain" for failure in store.failures(job_id))
    assert any(failure["failure_code"] == "skipped_outside_start_path" for failure in store.failures(job_id))


def test_discover_preserves_grouped_image_variants():
    def fetch(url):
        return """
            <main>
              <img src="/img/Monster/Achelous-100w.webp">
              <img src="/img/Monster/Achelous-200w.webp">
              <img src="/img/Monster/Achelous-540w.webp">
            </main>
        """

    store = JobStore()
    job_id = store.create(
        "crawl",
        status="created",
        source_url="https://example.com/games/start/",
        settings=DiscoverySettings(max_depth=0).to_dict(),
    )

    summary = discover(store, job_id, fetch_html=fetch)
    assets = store.assets(job_id)

    assert summary["assets_discovered"] == 1
    assert len(assets) == 1
    assert assets[0]["url"] == "https://example.com/img/Monster/Achelous-540w.webp"
    assert assets[0]["variant_count"] == 3
    assert [variant["label"] for variant in assets[0]["variants"]] == ["100w", "200w", "540w"]
