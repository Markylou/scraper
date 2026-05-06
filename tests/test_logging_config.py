import logging
from logging.handlers import RotatingFileHandler

import pytest

from page_scraper.logging_config import close_logging_handlers, configure_logging, get_logger


@pytest.fixture(autouse=True)
def clean_logging_handlers(tmp_path):
    close_logging_handlers()
    yield
    close_logging_handlers()


def test_configure_logging_creates_rotating_file_handler(tmp_path):
    log_file = tmp_path / "page_scraper.log"

    logger = configure_logging(log_file=log_file)
    logger.info("hello logging")

    assert log_file.exists()
    assert "hello logging" in log_file.read_text(encoding="utf-8")
    assert any(isinstance(handler, RotatingFileHandler) for handler in logger.handlers)


def test_configure_logging_is_idempotent_for_same_file(tmp_path):
    log_file = tmp_path / "page_scraper.log"

    first = configure_logging(log_file=log_file)
    second = configure_logging(log_file=log_file)

    assert first is second
    file_handlers = [
        handler
        for handler in second.handlers
        if isinstance(handler, RotatingFileHandler)
        and getattr(handler, "baseFilename", None) == str(log_file.resolve())
    ]
    assert len(file_handlers) == 1


def test_get_logger_returns_child_logger(tmp_path):
    configure_logging(log_file=tmp_path / "page_scraper.log")

    logger = get_logger("ui_server")

    assert logger.name == "page_scraper.ui_server"
    assert logger.getEffectiveLevel() == logging.INFO
