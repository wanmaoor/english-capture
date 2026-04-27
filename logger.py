"""Daily-file logger writing to <log_dir>/YYYY-MM-DD.log."""
import os
from datetime import datetime


class Logger:
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def log(self, level: str, message: str) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(self.log_dir, f"{today}.log")
        timestamp = datetime.now().isoformat()
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{level}] {message}\n")
