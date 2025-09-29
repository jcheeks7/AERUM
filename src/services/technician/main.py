"""Technician agent implemented on top of BaseService."""

from __future__ import annotations

import logging
import os
import time

from core.contracts import Command, Reply
from services._common import BaseService

SERVICE_NAME = "technician"
COMMAND_ADDRESS = os.getenv("TECHNICIAN_COMMAND_ADDR", "tcp://*:5002")
EVENT_FEED_ADDRESS = os.getenv("AERUM_EVENT_FEED", "tcp://127.0.0.1:7000")


class TechnicianService(BaseService):
    def __init__(self) -> None:
        super().__init__(
            name=SERVICE_NAME,
            command_address=COMMAND_ADDRESS,
            event_feed_address=EVENT_FEED_ADDRESS,
        )
        self._started_at = time.time()

    def handle(self, cmd: Command) -> Reply:
        if cmd.action == "noop":
            return Reply(
                src=self.name,
                dst=cmd.src,
                status="ok",
                payload={"message": "technician standing by"},
                correlation_id=cmd.correlation_id,
            )

        return Reply(
            src=self.name,
            dst=cmd.src,
            status="error",
            payload={"error": f"unknown action: {cmd.action}"},
            correlation_id=cmd.correlation_id,
        )

    def health_details(self) -> dict[str, float]:
        return {"uptime": time.time() - self._started_at}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    TechnicianService().run()


if __name__ == "__main__":
    main()

