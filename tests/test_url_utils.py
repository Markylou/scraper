from page_scraper.url_utils import classify_url, normalize_pasted_urls


def test_normalize_pasted_urls_accepts_lines_commas_and_duplicates():
    raw = """
    https://example.com/a
    https://example.com/a, https://example.com/b
    not-a-url
    """

    urls, rejected = normalize_pasted_urls(raw)

    assert urls == ["https://example.com/a", "https://example.com/b"]
    assert rejected == ["not-a-url"]


def test_classify_finalfantasy_fandom_wiki_url():
    assert classify_url("https://finalfantasy.fandom.com/wiki/Chichu") == "fandom"


def test_classify_general_https_url():
    assert classify_url("https://jegged.com/Games/Final-Fantasy-XIII-2/") == "general"
