from page_scraper.page_archive import (
    PageArchive,
    archive_page,
    content_markdown_from_html,
    extract_content_html,
    page_folder_name,
    page_folder_path,
    page_slug_from_title,
)


def test_page_slug_from_title_is_readable_and_stable():
    assert page_slug_from_title("Final Fantasy X / Abilities!") == "final-fantasy-x-abilities"


def test_page_folder_name_prefers_url_path_for_repeatable_archives():
    assert page_folder_name("Guide Page", "https://example.com/guides/intro.html") == "guides-intro"


def test_page_folder_path_mirrors_url_path_segments(tmp_path):
    folder = page_folder_path(
        "Armor",
        "https://jegged.com/Games/Final-Fantasy-X/Abilities/Equipment/Armor.html",
        tmp_path,
    )

    assert folder == tmp_path / "games" / "final-fantasy-x" / "abilities" / "equipment" / "armor"


def test_extract_content_html_keeps_main_content_and_removes_navigation():
    html = """
    <html>
      <head><title>Guide Page</title></head>
      <body>
        <nav>Skip this</nav>
        <main>
          <h1>Guide Page</h1>
          <p>Useful intro text.</p>
          <table><tr><th>Name</th><th>Value</th></tr><tr><td>A</td><td>1</td></tr></table>
        </main>
        <footer>Skip this too</footer>
      </body>
    </html>
    """

    content = extract_content_html(html)

    assert "Useful intro text." in content
    assert "<table>" in content
    assert "Skip this" not in content


def test_content_markdown_from_html_converts_headings_paragraphs_lists_and_tables():
    html = """
    <main>
      <!-- Navigation helper -->
      <h1>Guide Page</h1>
      <p>Useful intro text.</p>
      <ul><li>First item</li><li>Second item</li></ul>
      <table><tr><th>Name</th><th>Value</th></tr><tr><td>A</td><td>1</td></tr></table>
    </main>
    """

    markdown = content_markdown_from_html(html)

    assert "# Guide Page" in markdown
    assert "Useful intro text." in markdown
    assert "- First item" in markdown
    assert "| Name | Value |" in markdown
    assert "Navigation helper" not in markdown


def test_archive_page_writes_source_content_markdown_and_metadata(tmp_path):
    html = """
    <html>
      <head><title>Guide Page</title></head>
      <body>
        <main>
          <h1>Guide Page</h1>
          <p>Useful intro text.</p>
          <img src="/images/item.png">
          <a href="/next">Next page</a>
        </main>
      </body>
    </html>
    """

    archive = archive_page(
        url="https://example.com/guides/guide",
        final_url="https://example.com/guides/guide",
        title="Guide Page",
        html=html,
        strategy="requests",
        pages_dir=tmp_path,
    )

    assert archive == PageArchive(
        folder=tmp_path / "guides" / "guide",
        source_file=tmp_path / "guides" / "guide" / "source.html",
        content_html_file=tmp_path / "guides" / "guide" / "content.html",
        markdown_file=tmp_path / "guides" / "guide" / "content.md",
        metadata_file=tmp_path / "guides" / "guide" / "metadata.json",
    )
    assert archive.source_file.read_text(encoding="utf-8") == html
    assert "Useful intro text." in archive.content_html_file.read_text(encoding="utf-8")
    assert "# Guide Page" in archive.markdown_file.read_text(encoding="utf-8")
    metadata = archive.metadata_file.read_text(encoding="utf-8")
    assert '"source_url": "https://example.com/guides/guide"' in metadata
    assert '"path": "guides/guide"' in metadata
    assert '"images": [' in metadata
    assert '"https://example.com/images/item.png"' in metadata
