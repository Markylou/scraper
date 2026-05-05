from dataclasses import dataclass

import requests


USER_AGENT = "PageScraper/0.1 (local research tool)"
REQUEST_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class FetchResult:
    requested_url: str
    final_url: str
    status_code: int
    content_type: str | None
    body: bytes
    text: str | None
    fetch_strategy: str

    @property
    def url(self) -> str:
        return self.requested_url

    @property
    def html(self) -> str:
        return self.text or ""


def fetch_url(url: str) -> FetchResult:
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return FetchResult(
        requested_url=url,
        final_url=response.url,
        status_code=response.status_code,
        content_type=response.headers.get("Content-Type"),
        body=response.content,
        text=decode_response_html(response),
        fetch_strategy="requests",
    )


def decode_response_html(response) -> str:
    encoding = (response.encoding or "").lower()
    apparent = (response.apparent_encoding or "").lower()
    if encoding in {"iso-8859-1", "latin-1"} and apparent in {"utf-8", "utf_8"}:
        return response.content.decode("utf-8", errors="replace")
    return response.text


def html_needs_browser(html: str) -> bool:
    compact = " ".join(html.lower().split())
    if len(compact) < 500:
        return True

    browser_markers = [
        "please enable javascript",
        "enable javascript to continue",
        "you need to enable javascript",
        "checking your browser",
    ]
    return any(marker in compact for marker in browser_markers)
