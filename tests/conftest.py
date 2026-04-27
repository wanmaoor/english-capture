"""Shared pytest fixtures."""
import json
import os
from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Empty Obsidian vault rooted at tmp_path; create the 20-Areas/英语 dir."""
    area = tmp_path / "20-Areas" / "英语"
    area.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_config(tmp_path: Path) -> dict:
    """Minimal config dict for tests that need one."""
    return {
        "openrouter_api_key": "test-key",
        "openrouter_model": "qwen/qwen3-235b-a22b-2507",
        "vault_path": str(tmp_path),
        "timeout_seconds": 30,
    }
