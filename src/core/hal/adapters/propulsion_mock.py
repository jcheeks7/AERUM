"""Mock propulsion adapter implementing the HAL interface."""

from __future__ import annotations

import logging
import random
from typing import Any, Dict

from core.hal.base import Propulsion


class PropulsionMock(Propulsion):
    """Simple propulsion mock producing pseudo telemetry."""

    def __init__(self) -> None:
        self._armed = False
        self._last_telemetry: Dict[str, Any] = {"prop_pressure": 50.0, "temperature": 295.0}

    def arm(self) -> Dict[str, Any]:
        self._armed = True
        return {"armed": True}

    def fire(self, duration_s: float, valve_id: str) -> Dict[str, Any]:
        logging.info("Mock propulsion firing valve %s for %.2fs", valve_id, duration_s)
        pressure = random.uniform(10.0, 60.0)
        telemetry = {"prop_pressure": pressure, "valve_id": valve_id, "duration_s": duration_s}
        self._last_telemetry.update(telemetry)
        return telemetry

    def disarm(self) -> Dict[str, Any]:
        self._armed = False
        return {"armed": False}

    def read_sensors(self) -> Dict[str, Any]:
        snapshot = {
            "prop_pressure": random.uniform(20.0, 65.0) if self._armed else self._last_telemetry.get("prop_pressure", 15.0),
            "temperature": random.uniform(280.0, 320.0),
            "armed": self._armed,
        }
        self._last_telemetry.update(snapshot)
        return snapshot
