"""Mission Lead service implemented as a BaseService subclass."""

from __future__ import annotations

import logging
import os

import zmq

from core.contracts import Command, Reply
from core.ipc import make_req
from services._common import BaseService

SERVICE_NAME = "mission_lead"
COMMAND_ADDRESS = os.getenv("MISSION_LEAD_COMMAND_ADDR", "tcp://*:5001")
EVENT_FEED_ADDRESS = os.getenv("AERUM_EVENT_FEED", "tcp://127.0.0.1:7000")
TECHNICIAN_ADDR = os.getenv("TECHNICIAN_COMMAND_ADDR", "tcp://127.0.0.1:5002")
TECHNICIAN_CLIENT_ADDR = os.getenv("TECHNICIAN_CLIENT_ADDR", TECHNICIAN_ADDR)


class MissionLeadService(BaseService):
    def __init__(self) -> None:
        super().__init__(
            name=SERVICE_NAME,
            command_address=COMMAND_ADDRESS,
            event_feed_address=EVENT_FEED_ADDRESS,
        )
        self._service_registry = {"technician": TECHNICIAN_CLIENT_ADDR}

    def handle(self, cmd: Command) -> Reply:
        logging.info("Mission Lead handling %s", cmd.action)
        if cmd.action == "noop":
            return Reply(
                src=self.name,
                dst=cmd.src,
                status="ok",
                payload={"message": "noop acknowledged"},
                correlation_id=cmd.correlation_id,
            )

        if cmd.action == "echo":
            return Reply(
                src=self.name,
                dst=cmd.src,
                status="ok",
                payload={"echo": cmd.payload},
                correlation_id=cmd.correlation_id,
            )

        if cmd.action == "delegate":
            return self._handle_delegate(cmd)

        return Reply(
            src=self.name,
            dst=cmd.src,
            status="error",
            payload={"error": f"unknown action: {cmd.action}"},
            correlation_id=cmd.correlation_id,
        )

    # ------------------------------------------------------------------
    # Delegate handling
    # ------------------------------------------------------------------
    def _handle_delegate(self, cmd: Command) -> Reply:
        target = cmd.payload.get("target")
        action = cmd.payload.get("action", "noop")
        payload = cmd.payload.get("payload", {})

        if not isinstance(target, str):
            return self._error_reply(cmd, "delegate requires target")
        if not isinstance(payload, dict):
            return self._error_reply(cmd, "delegate payload must be an object")

        address = self._service_registry.get(target)
        if not address:
            return self._error_reply(cmd, f"unknown target: {target}")

        child_cmd = Command(
            src=self.name,
            dst=target,
            action=action,
            payload=payload,
        )

        socket = make_req(zmq.Context.instance(), address)
        try:
            socket.send_string(child_cmd.to_json())
            raw = socket.recv_string()
        finally:
            socket.close(linger=0)

        child_reply = Reply.from_json(raw)
        self.emit_event(
            topic=f"delegate.{target}",
            payload={
                "command": child_cmd.to_dict(),
                "reply": child_reply.to_dict(),
            },
        )

        return Reply(
            src=self.name,
            dst=cmd.src,
            status=child_reply.status,
            payload={"delegate": child_reply.to_dict()},
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
    service = MissionLeadService()
    service.run()


if __name__ == "__main__":
    main()

