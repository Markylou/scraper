from page_scraper.scrape_service import choose_strategy


def test_choose_strategy_uses_fandom_for_finalfantasy_fandom_wiki():
    assert choose_strategy("https://finalfantasy.fandom.com/wiki/Chichu") == "fandom"


def test_choose_strategy_uses_requests_first_for_general_url():
    assert choose_strategy("https://jegged.com/Games/Final-Fantasy-XIII-2/") == "requests"
