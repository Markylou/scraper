from page_scraper.core.job_output import job_output_root, site_slug_from_url


def test_job_output_root_uses_site_slug_and_short_job_id(tmp_path):
    root = job_output_root("https://jegged.com/Games/Final-Fantasy-X/", "abcdef123456", jobs_dir=tmp_path)

    assert root == tmp_path / "jegged_abcdef12"


def test_site_slug_uses_root_domain_without_tld():
    assert site_slug_from_url("https://guides.gamercorner.net/ffxiii-2/weapons/") == "gamercorner"
