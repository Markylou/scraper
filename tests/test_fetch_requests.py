from page_scraper.fetch_requests import FetchResult, decode_response_html, html_needs_browser


def test_html_needs_browser_when_page_is_too_small():
    assert html_needs_browser("<html></html>") is True


def test_html_needs_browser_when_common_javascript_shell_is_present():
    html = "<html><body><noscript>Please enable JavaScript</noscript></body></html>"
    assert html_needs_browser(html) is True


def test_html_does_not_need_browser_when_content_has_real_body_text():
    html = "<html><head><title>Guide</title></head><body><main>" + ("Useful text " * 80) + "</main></body></html>"
    assert html_needs_browser(html) is False


def test_fetch_result_shape():
    result = FetchResult(url="https://example.com", final_url="https://example.com", html="<html></html>", status_code=200)
    assert result.url == "https://example.com"
    assert result.status_code == 200


def test_decode_response_html_prefers_utf8_when_requests_guesses_latin1():
    class Response:
        encoding = "ISO-8859-1"
        apparent_encoding = "utf-8"
        content = "Tidus\u2019s".encode("utf-8")
        text = content.decode("ISO-8859-1")

    assert decode_response_html(Response()) == "Tidus\u2019s"
