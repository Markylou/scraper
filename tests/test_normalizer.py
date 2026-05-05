from page_scraper.core.normalizer import (
    is_supported_url,
    normalize_url,
    same_domain,
    under_start_path,
    url_identity_key,
)


def test_normalize_url_joins_relative_and_removes_fragment():
    assert normalize_url("../Blitzball/#top", "https://jegged.com/Games/Final-Fantasy-X/Abilities/") == (
        "https://jegged.com/Games/Final-Fantasy-X/Blitzball/"
    )


def test_normalize_url_rejects_unsupported_schemes():
    assert normalize_url("mailto:test@example.com") is None
    assert normalize_url("javascript:void(0)") is None


def test_url_identity_key_normalizes_case_and_trailing_slash():
    assert url_identity_key("HTTPS://JEGGED.COM/Games/Final-Fantasy-X") == (
        "https://jegged.com/Games/Final-Fantasy-X/"
    )


def test_same_domain_and_start_path_boundaries():
    root = "https://jegged.com/Games/Final-Fantasy-X/"
    assert same_domain("https://jegged.com/Games/Final-Fantasy-X/Abilities/", root)
    assert not same_domain("https://example.com/Games/Final-Fantasy-X/", root)
    assert under_start_path("https://jegged.com/Games/Final-Fantasy-X/Abilities/", root)
    assert not under_start_path("https://jegged.com/Games/Final-Fantasy-VII/", root)


def test_query_string_is_preserved():
    assert normalize_url("/search?q=tidus#results", "https://jegged.com/Games/") == (
        "https://jegged.com/search/?q=tidus"
    )


def test_is_supported_url_requires_http_or_https():
    assert is_supported_url("https://example.com")
    assert is_supported_url("http://example.com")
    assert not is_supported_url("ftp://example.com/file.txt")
