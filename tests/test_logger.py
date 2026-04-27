"""Tests for logger.py."""
from datetime import datetime
from pathlib import Path

from logger import Logger


def test_log_creates_file_in_log_dir(tmp_path: Path):
    log_dir = tmp_path / "logs"
    logger = Logger(str(log_dir))
    logger.log("INFO", "hello")

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{today}.log"
    assert log_file.exists()
    assert "hello" in log_file.read_text()


def test_log_includes_level_and_timestamp(tmp_path: Path):
    log_dir = tmp_path / "logs"
    logger = Logger(str(log_dir))
    logger.log("WARN", "watch out")

    today = datetime.now().strftime("%Y-%m-%d")
    content = (log_dir / f"{today}.log").read_text()
    assert "[WARN]" in content
    assert "watch out" in content
    assert content.startswith("[")  # ISO timestamp


def test_log_appends_multiple_entries(tmp_path: Path):
    log_dir = tmp_path / "logs"
    logger = Logger(str(log_dir))
    logger.log("INFO", "first")
    logger.log("INFO", "second")

    today = datetime.now().strftime("%Y-%m-%d")
    content = (log_dir / f"{today}.log").read_text()
    assert content.count("INFO") == 2


def test_log_dir_created_on_init(tmp_path: Path):
    log_dir = tmp_path / "deep" / "logs"
    Logger(str(log_dir))
    assert log_dir.exists()
