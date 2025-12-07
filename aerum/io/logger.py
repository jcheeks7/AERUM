"""Lightweight text logger used by the AERUM agents and controller."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from aerum.core.config import AERUMConfig


class Logger:
    """Append-only mission logger writing timestamped text entries."""

    def __init__(self, config: Optional[AERUMConfig] = None):
        self.config = config or AERUMConfig()
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logs_dir = self.config.logs_dir
        logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = Path(logs_dir) / f"mission_log_{timestamp}.txt"

    def log(self, agent: str, message: str) -> None:
        timestamp = datetime.now().isoformat()
        full_message = f"[{timestamp}] [{agent}] {message}"
        print(full_message)
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(full_message + "\n")
