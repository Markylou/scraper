from page_scraper.core.asset_discovery import classify_asset_url, discover_assets, image_variant_key


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


def test_image_variant_key_groups_width_suffixes_but_not_descriptive_words():
    assert (
        image_variant_key("https://jegged.com/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-100w.webp")
        == image_variant_key("https://jegged.com/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-540w.webp")
    )
    assert (
        image_variant_key("https://jegged.com/img/Games/Final-Fantasy-X/Maps/Sea-of-Sorrow-Map-540w.webp")
        == image_variant_key("https://jegged.com/img/Games/Final-Fantasy-X/Maps/Sea-of-Sorrow-Map.webp")
    )
    assert (
        image_variant_key("https://jegged.com/img/Games/Final-Fantasy-X/Icons/Vial-Green-Large.webp")
        != image_variant_key("https://jegged.com/img/Games/Final-Fantasy-X/Icons/Vial-Green-Small.webp")
    )


def test_discover_assets_groups_exact_duplicates_and_selects_best_width_variant():
    html = """
    <main>
      <img src="/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-100w.webp">
      <img src="/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-100w.webp">
      <img src="/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-200w.webp">
      <img src="/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-540w.webp">
      <img src="/img/Games/Final-Fantasy-X/Icons/Vial-Green-Large.webp">
      <img src="/img/Games/Final-Fantasy-X/Icons/Vial-Green-Small.webp">
    </main>
    """

    assets = discover_assets(html, "https://jegged.com/Games/Final-Fantasy-X/")
    by_url = {asset["url"]: asset for asset in assets}

    assert "https://jegged.com/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-540w.webp" in by_url
    assert "https://jegged.com/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-100w.webp" not in by_url
    assert len([asset for asset in assets if "Achelous" in asset["url"]]) == 1
    assert len(by_url["https://jegged.com/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-540w.webp"]["variants"]) == 3
    assert by_url["https://jegged.com/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-540w.webp"]["occurrence_count"] == 4
    assert by_url["https://jegged.com/img/Games/Final-Fantasy-X/Monster-Arena/Achelous-540w.webp"]["variants"][0]["occurrence_count"] == 2
    assert by_url["https://jegged.com/img/Games/Final-Fantasy-X/Icons/Vial-Green-Large.webp"]["variant_count"] == 1
    assert by_url["https://jegged.com/img/Games/Final-Fantasy-X/Icons/Vial-Green-Small.webp"]["variant_count"] == 1
