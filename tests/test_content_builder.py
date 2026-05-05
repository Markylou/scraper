from page_scraper.content_builder import rebuild_page_content
from page_scraper.page_archive import archive_page


def test_rebuild_page_content_walks_nested_page_folders(tmp_path):
    archive_page(
        url="https://example.com/games/final-fantasy-x/",
        final_url="https://example.com/games/final-fantasy-x/",
        title="Final Fantasy X",
        html="<html><body><main><h1>Final Fantasy X</h1><p>Guide.</p></main></body></html>",
        strategy="requests",
        pages_dir=tmp_path,
    )

    result = rebuild_page_content(pages_dir=tmp_path)

    assert result["rebuilt"] == ["games/final-fantasy-x"]
