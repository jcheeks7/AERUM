"""Fault Analyst (FDIR) service monitoring telemetry and health."""

from __future__ import annotations

import logging
import os
import threading
from typing import Any

import zmq

from core.contracts import Command, Event, Health, Reply
from core.ipc import TOPIC_EVENTS, TOPIC_HEALTH, make_req, make_sub
from services._common import BaseService

SERVICE_NAME = "fault_analyst"
COMMAND_ADDRESS = os.getenv("FAULT_ANALYST_COMMAND_ADDR", "tcp://*:5003")
EVENT_FEED_ADDRESS = os.getenv("AERUM_EVENT_FEED", "tcp://127.0.0.1:7000")
MISSION_LEAD_CLIENT_ADDR = os.getenv("MISSION_LEAD_CLIENT_ADDR", "tcp://127.0.0.1:5001")


class FaultAnalystService(BaseService):
    """Service applying simple FDIR rules to telemetry streams."""

    def __init__(self) -> None:
        super().__init__(
            name=SERVICE_NAME,
            command_address=COMMAND_ADDRESS,
            event_feed_address=EVENT_FEED_ADDRESS,
        )
        self._ctx = zmq.Context.instance()
        self._sub = make_sub(
            self._ctx,
            self.event_feed_address,
            topics=[TOPIC_EVENTS, TOPIC_HEALTH],
            bind=False,
        )
        self._monitor_stop = threading.Event()
        self._monitor_thread = threading.Thread(
            target=self._monitor_streams,
            name="fault-analyst-monitor",
            daemon=True,
        )
        self._mission_lead_addr = MISSION_LEAD_CLIENT_ADDR

    def run(self) -> None:  # pragma: no cover - delegates to BaseService
        if not self._monitor_thread.is_alive():
            self._monitor_thread.start()
        super().run()

    def stop(self) -> None:
        self._monitor_stop.set()
        try:
            self._sub.close(linger=0)
        except zmq.error.ZMQError:  # pragma: no cover - defensive cleanup
            pass
        if self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1)
        super().stop()

    def handle(self, cmd: Command) -> Reply:
        logging.info("Fault Analyst handling %s", cmd.action)
        if cmd.action == "noop":
            return Reply(
                src=self.name,
                dst=cmd.src,
                status="ok",
                payload={"message": "FDIR active"},
                correlation_id=cmd.correlation_id,
            )
        return Reply(
            src=self.name,
            dst=cmd.src,
            status="error",
            payload={"error": f"unknown action: {cmd.action}"},
            correlation_id=cmd.correlation_id,
        )

    # ------------------------------------------------------------------
    # Monitoring helpers
    # ------------------------------------------------------------------
    def _monitor_streams(self) -> None:
        poller = zmq.Poller()
        poller.register(self._sub, zmq.POLLIN)
        while not self._monitor_stop.is_set():
            if not self._running.wait(timeout=0.1):
                continue
            try:
                events = dict(poller.poll(timeout=200))
            except zmq.error.ZMQError:
                if self._monitor_stop.is_set():
                    break
                raise
            if self._sub not in events:
                continue
            try:
                message = self._sub.recv_string(flags=zmq.NOBLOCK)
            except zmq.Again:
                continue
            except zmq.error.ZMQError:
                if self._monitor_stop.is_set():
                    break
                raise
            self._process_stream_message(message)

    def _process_stream_message(self, message: str) -> None:
        try:
            topic, payload = message.split(" ", 1)
        except ValueError:
            logging.warning("Fault Analyst received malformed message: %s", message)
            return

        if topic == TOPIC_EVENTS:
            event = Event.from_json(payload)
            self._evaluate_event(event)
        elif topic == TOPIC_HEALTH:
            health = Health.from_json(payload)
            self._evaluate_health(health)

    def _evaluate_event(self, event: Event) -> None:
        payload = event.payload
        if not isinstance(payload, dict):
            return
        pressure = payload.get("prop_pressure")
        if isinstance(pressure, (int, float)) and pressure < 20.0:
            self._raise_alarm({"code": "PROP_PRESSURE_LOW", "pressure": pressure})

    def _evaluate_health(self, health: Health) -> None:
        if health.status == "FAILED":
            self._raise_alarm({"code": "AGENT_FAILED", "agent": health.src})

    def _raise_alarm(self, details: dict[str, Any]) -> None:
        self.emit_event(topic="fdir.alarm", payload=details, level="ALARM")
        self._suggest_safe_mode(details)

    def _suggest_safe_mode(self, details: dict[str, Any]) -> None:
        if not self._mission_lead_addr:
            return
        socket = make_req(self._ctx, self._mission_lead_addr)
        socket.setsockopt(zmq.RCVTIMEO, 1000)
        socket.setsockopt(zmq.SNDTIMEO, 1000)
        command = Command(
            src=self.name,
            dst="mission_lead",
            action="delegate",
            payload={
                "target": "mission_lead",
                "action": "safe_mode",
                "payload": details,
            },
        )
        try:
            socket.send_string(command.to_json())
            # Best-effort receive; timeout will raise ZMQError which is ignored.
            try:
                socket.recv_string()
            except zmq.error.ZMQError:
                logging.info("Mission Lead did not respond to safe_mode suggestion")
        except zmq.error.ZMQError:
            logging.exception("Failed to send safe_mode suggestion to Mission Lead")
        finally:
            socket.close(linger=0)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    FaultAnalystService().run()


if __name__ == "__main__":
    main()
