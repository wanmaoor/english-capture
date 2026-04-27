"""Tests for queue.py."""
from pathlib import Path

from queue import QueueManager


def test_load_returns_empty_when_file_missing(tmp_path: Path):
    q = QueueManager(str(tmp_path / "queue.json"))
    assert q.load() == []


def test_add_persists_item(tmp_path: Path):
    path = tmp_path / "queue.json"
    q = QueueManager(str(path))
    q.add({"input": "hello"})

    q2 = QueueManager(str(path))
    assert q2.load() == [{"input": "hello"}]


def test_add_appends_to_existing(tmp_path: Path):
    path = tmp_path / "queue.json"
    q = QueueManager(str(path))
    q.add({"a": 1})
    q.add({"b": 2})
    assert q.load() == [{"a": 1}, {"b": 2}]


def test_clear_removes_file(tmp_path: Path):
    path = tmp_path / "queue.json"
    q = QueueManager(str(path))
    q.add({"x": 1})
    q.clear()
    assert not path.exists()
    assert q.load() == []


def test_add_creates_parent_dir(tmp_path: Path):
    path = tmp_path / "deep" / "nested" / "queue.json"
    q = QueueManager(str(path))
    q.add({"x": 1})
    assert path.exists()
