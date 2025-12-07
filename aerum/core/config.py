"""Configuration utilities for AERUM runtime components."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class AERUMConfig:
    """Lightweight configuration loader for directory and runtime settings."""

    def __init__(self, root: Optional[Path] = None, config_path: Optional[Path] = None):
        self.root = Path(root or Path(__file__).resolve().parents[2])
        self.config_path = Path(config_path or (self.root / "config.json"))
        self._data: Dict[str, Any] = self._load_config()

        self.logs_dir = Path(self._data.get("logs_dir", self.root / "logs"))
        self.missions_dir = Path(self._data.get("missions_dir", self.root / "aerum" / "missions"))
        self.tick_rate = float(self._data.get("tick_rate", 0.5))

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with self.config_path.open("r", encoding="utf-8") as handle:
                    return json.load(handle)
            except Exception:
                return {}
        return {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": str(self.root),
            "logs_dir": str(self.logs_dir),
            "missions_dir": str(self.missions_dir),
            "tick_rate": self.tick_rate,
        }
