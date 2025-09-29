"""Mock power subsystem adapter."""

from __future__ import annotations

import random
from typing import Any, Dict

from core.hal.base import Power


class PowerMock(Power):
    """Produce synthetic battery telemetry and switch acknowledgements."""

    def read_battery(self) -> Dict[str, Any]:
        return {"state_of_charge": random.uniform(70.0, 100.0)}

    def switch(self, mode: str) -> Dict[str, Any]:
        return {"mode": mode, "ok": True}
