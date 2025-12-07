"""Mission engine responsible for loading and stepping through mission scripts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


class MissionEngine:
    """Loads mission definitions and tracks step progression."""

    def __init__(self, missions_dir: Path):
        self.missions_dir = missions_dir
        self._steps: List[dict] = []
        self._current_index: int = -1
        self.metadata: Dict[str, str] = {}

    def load(self, mission_name: str) -> None:
        mission_path = self.missions_dir / mission_name
        with mission_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        self.metadata = {
            "name": data.get("name", mission_path.stem.replace("_", " ")),
            "file": mission_path.name,
            "description": data.get("description", ""),
        }
        self._steps = data.get("steps", [])
        self._current_index = -1

    def available_missions(self) -> List[Dict[str, str]]:
        missions: List[Dict[str, str]] = []
        for path in sorted(self.missions_dir.glob("*.json")):
            name = path.stem.replace("_", " ")
            description = ""
            try:
                with path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    name = data.get("name", name)
                    description = data.get("description", description)
            except Exception:
                pass
            missions.append({"file": path.name, "name": name, "description": description})
        return missions

    def get_current_step(self) -> Optional[dict]:
        if 0 <= self._current_index < len(self._steps):
            return self._steps[self._current_index]
        return None

    def get_next_step(self) -> Optional[dict]:
        next_index = self._current_index + 1
        if 0 <= next_index < len(self._steps):
            return self._steps[next_index]
        return None

    def advance(self) -> Optional[dict]:
        if self._current_index + 1 >= len(self._steps):
            return None
        self._current_index += 1
        return self._steps[self._current_index]

    def is_complete(self) -> bool:
        return self._current_index >= len(self._steps) - 1 and bool(self._steps)

    def progress(self) -> float:
        if not self._steps:
            return 0.0
        return max(0.0, min(1.0, (self._current_index + 1) / len(self._steps)))

    def to_status(self) -> dict:
        return {
            "mission_name": self.metadata.get("name"),
            "current_step": self.get_current_step(),
            "next_step": self.get_next_step(),
            "progress": self.progress(),
        }
