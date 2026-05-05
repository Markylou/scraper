import json

from page_scraper.core.crawler import DiscoverySettings
from page_scraper.core.downloader import download_selected
from page_scraper.core.manifest import write_manifest
from page_scraper.job_store import JobStore


def test_download_selected_writes_pages_assets_and_manifest(tmp_path):
    store = JobStore()
    job_id = store.create(
        "crawl",
        status="ready",
        source_url="https://example.com/games/start/",
        settings=DiscoverySettings(max_depth=1).to_dict(),
    )
    page = store.upsert_page(job_id, "https://example.com/games/start/", 0, None, title="Start")
    asset = store.upsert_asset(job_id, "https://example.com/images/logo.png", "image", page["id"])

    def fetch_page(url):
        return "<html><body><main><h1>Start</h1><p>Saved.</p></main></body></html>"

    def fetch_asset(url):
        return b"image bytes", "image/png"

    result = download_selected(store, job_id, jobs_dir=tmp_path, fetch_page_html=fetch_page, fetch_asset=fetch_asset)

    assert result["pages_downloaded"] == 1
    assert result["assets_downloaded"] == 1
    job = store.get(job_id)
    assert job["status"] == "completed"
    assert (tmp_path / f"example_{job_id[:8]}" / "pages" / "games" / "start" / "source.html").exists()
    assert store.assets(job_id)[0]["local_path"].startswith("assets/images/logo-")

    manifest_path = write_manifest(store, job_id)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["summary"]["pagesDownloaded"] == 1
    assert manifest["summary"]["assetsDownloaded"] == 1
    assert manifest["downloadedPages"][0].endswith("source.html")
    assert manifest["downloadedAssets"][0].startswith("assets/images/logo-")
