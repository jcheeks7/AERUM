"""Base service template for AERUM ZeroMQ services."""

from __future__ import annotations

import logging
import os
import signal
import threading
import time
from typing import Any, Callable

import zmq

from core.contracts import Command, Event, Health, Reply
from core.ipc import TOPIC_EVENTS, TOPIC_HEALTH, make_pub, make_rep

DEFAULT_EVENT_FEED = os.getenv("AERUM_EVENT_FEED", "tcp://127.0.0.1:7000")


class BaseService:
    """Base class providing command handling and health publication."""

    def __init__(
        self,
        name: str,
        command_address: str,
        *,
        event_feed_address: str | None = None,
        health_interval: float = 1.0,
    ) -> None:
        self.name = name
        self.command_address = command_address
        self.event_feed_address = event_feed_address or DEFAULT_EVENT_FEED
        self.health_interval = health_interval

        self._ctx = zmq.Context.instance()
        self._rep = make_rep(self._ctx, self.command_address)
        self._pub = make_pub(self._ctx, self.event_feed_address, bind=False)

        self._running = threading.Event()
        self._health_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Start the service, serving commands until stopped."""

        self._running.set()
        self._health_thread = threading.Thread(target=self._health_loop, daemon=True)
        self._health_thread.start()
        self._install_signal_handlers(self.stop)

        logging.info("%s service ready on %s", self.name, self.command_address)

        try:
            while self._running.is_set():
                try:
                    payload = self._rep.recv_string()
                except zmq.error.ZMQError as exc:
                    if not self._running.is_set():
                        break
                    raise exc
                self._process_command(payload)
        finally:
            self.stop()

    def stop(self) -> None:
        if not self._running.is_set():
            return

        self._running.clear()
        logging.info("Stopping %s service", self.name)
        self._rep.close(linger=0)
        self._pub.close(linger=0)
        if self._health_thread:
            self._health_thread.join(timeout=1)

    # ------------------------------------------------------------------
    # Command processing
    # ------------------------------------------------------------------
    def _process_command(self, payload: str) -> None:
        cmd: Command | None = None
        try:
            cmd = Command.from_json(payload)
            reply = self.handle(cmd)
        except Exception as exc:  # pragma: no cover - defensive
            logging.exception("Error handling command")
            reply = Reply(
                src=self.name,
                dst=cmd.src if cmd else "unknown",
                status="error",
                payload={"error": str(exc)},
                correlation_id=cmd.correlation_id if cmd else "",
            )

        self._rep.send_string(reply.to_json())
        event_payload = {"reply": reply.to_dict()}
        if cmd is not None:
            event_payload["command"] = cmd.to_dict()
        self.emit_event(
            topic=f"command.{reply.status}",
            payload=event_payload,
            level="info" if reply.status == "ok" else "error",
        )

    # ------------------------------------------------------------------
    # Hooks for subclasses
    # ------------------------------------------------------------------
    def handle(self, cmd: Command) -> Reply:  # pragma: no cover - abstract method
        raise NotImplementedError

    def health_details(self) -> dict[str, Any]:  # pragma: no cover - optional override
        return {}

    # ------------------------------------------------------------------
    # Messaging helpers
    # ------------------------------------------------------------------
    def emit_event(self, topic: str, payload: dict[str, Any], level: str = "info") -> None:
        event = Event(src=self.name, level=level, topic=topic, payload=payload)
        self._pub.send_string(f"{TOPIC_EVENTS} {event.to_json()}")

    def publish_health(self, status: str = "ok", details: dict[str, Any] | None = None) -> None:
        health = Health(src=self.name, status=status, details=details or self.health_details())
        self._pub.send_string(f"{TOPIC_HEALTH} {health.to_json()}")

    # ------------------------------------------------------------------
    # Background loops
    # ------------------------------------------------------------------
    def _health_loop(self) -> None:
        while self._running.is_set():
            self.publish_health()
            time.sleep(self.health_interval)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------
    def _install_signal_handlers(self, cleanup: Callable[[], None]) -> None:
        def handler(signum, _frame):  # pragma: no cover - best effort cleanup
            logging.info("Signal %s received by %s", signum, self.name)
            cleanup()
            raise SystemExit(0)

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

