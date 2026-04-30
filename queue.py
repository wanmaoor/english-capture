from __future__ import annotations

"""File-backed retry queue for failed LLM calls."""
import json
import os
from typing import Any


class QueueManager:
    def __init__(self, path: str):
        self.path = path

    def load(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def add(self, item: dict[str, Any]) -> None:
        items = self.load()
        items.append(item)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    def clear(self) -> None:
        if os.path.exists(self.path):
            os.remove(self.path)
