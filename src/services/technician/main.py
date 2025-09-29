"""Technician agent implemented on top of BaseService."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict

from core.contracts import Command, Reply
from core.hal.adapters.propulsion_mock import PropulsionMock
from core.hal.base import Propulsion
from services._common import BaseService

SERVICE_NAME = "technician"
COMMAND_ADDRESS = os.getenv("TECHNICIAN_COMMAND_ADDR", "tcp://*:5002")
EVENT_FEED_ADDRESS = os.getenv("AERUM_EVENT_FEED", "tcp://127.0.0.1:7000")


class TechnicianService(BaseService):
    def __init__(self, propulsion: Propulsion | None = None) -> None:
        super().__init__(
            name=SERVICE_NAME,
            command_address=COMMAND_ADDRESS,
            event_feed_address=EVENT_FEED_ADDRESS,
        )
        self._started_at = time.time()
        self._propulsion = propulsion or PropulsionMock()

    def handle(self, cmd: Command) -> Reply:
        if cmd.action == "noop":
            return Reply(
                src=self.name,
                dst=cmd.src,
                status="ok",
                payload={"message": "technician standing by"},
                correlation_id=cmd.correlation_id,
            )

        if cmd.action == "arm_propulsion":
            return self._handle_arm(cmd)

        if cmd.action == "fire_thruster":
            return self._handle_fire(cmd)

        if cmd.action == "disarm_propulsion":
            return self._handle_disarm(cmd)

        if cmd.action == "read_propulsion":
            return self._handle_read(cmd)

        return Reply(
            src=self.name,
            dst=cmd.src,
            status="error",
            payload={"error": f"unknown action: {cmd.action}"},
            correlation_id=cmd.correlation_id,
        )

    def health_details(self) -> dict[str, float]:
        return {"uptime": time.time() - self._started_at}

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def _handle_arm(self, cmd: Command) -> Reply:
        result = self._propulsion.arm()
        return self._ok_reply(cmd, {"arm": result})

    def _handle_fire(self, cmd: Command) -> Reply:
        payload = cmd.payload or {}
        duration = payload.get("duration_s")
        valve_id = payload.get("valve_id")

        if not isinstance(duration, (int, float)) or not isinstance(valve_id, str):
            return self._error_reply(cmd, "fire_thruster requires duration_s (number) and valve_id (string)")

        telemetry = self._propulsion.fire(float(duration), valve_id)
        self._publish_telemetry(telemetry)
        return self._ok_reply(cmd, {"telemetry": telemetry})

    def _handle_disarm(self, cmd: Command) -> Reply:
        result = self._propulsion.disarm()
        return self._ok_reply(cmd, {"disarm": result})

    def _handle_read(self, cmd: Command) -> Reply:
        telemetry = self._propulsion.read_sensors()
        self._publish_telemetry(telemetry)
        return self._ok_reply(cmd, {"telemetry": telemetry})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _publish_telemetry(self, telemetry: Dict[str, Any]) -> None:
        self.emit_event(topic="telemetry.propulsion", payload=dict(telemetry))

    def _ok_reply(self, cmd: Command, payload: Dict[str, Any]) -> Reply:
        return Reply(
            src=self.name,
            dst=cmd.src,
            status="ok",
            payload=payload,
            correlation_id=cmd.correlation_id,
        )

    def _error_reply(self, cmd: Command, message: str) -> Reply:
        return Reply(
            src=self.name,
            dst=cmd.src,
            status="error",
            payload={"error": message},
            correlation_id=cmd.correlation_id,
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    TechnicianService().run()


if __name__ == "__main__":
    main()

