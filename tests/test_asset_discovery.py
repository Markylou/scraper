from page_scraper.core.asset_discovery import classify_asset_url, discover_assets


def test_classify_asset_url():
    assert classify_asset_url("https://example.com/image.png") == "image"
    assert classify_asset_url("https://example.com/file.pdf") == "document"
    assert classify_asset_url("https://example.com/movie.mp4") == "video"
    assert classify_asset_url("https://example.com/sound.mp3") == "audio"
    assert classify_asset_url("https://example.com/page") == "other"


def test_discover_assets_finds_images_srcset_and_documents():
    html = """
    <main>
      <img src="/images/logo.png">
      <img data-src="/images/lazy.webp">
      <source srcset="/images/a.png 1x, /images/b.png 2x">
      <a href="/docs/guide.pdf">Guide</a>
      <a href="/video/intro.mp4">Video</a>
    </main>
    """

    assets = discover_assets(html, "https://example.com/games/")
    by_url = {asset["url"]: asset for asset in assets}

    assert by_url["https://example.com/images/logo.png"]["asset_type"] == "image"
    assert by_url["https://example.com/images/lazy.webp"]["selected"] is True
    assert by_url["https://example.com/images/a.png"]["asset_type"] == "image"
    assert by_url["https://example.com/docs/guide.pdf"]["asset_type"] == "document"
    assert by_url["https://example.com/video/intro.mp4"]["selected"] is True
