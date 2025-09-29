"""Datastore service for persisting events and health telemetry."""

from __future__ import annotations

import logging
import os
import signal
import sqlite3
from contextlib import closing
from typing import Callable

import zmq

from src.core.contracts import Event, Health
from src.core.ipc import TOPIC_EVENTS, TOPIC_HEALTH, make_sub

DB_PATH = os.getenv("AERUM_DB_PATH", "aerum.db")
EVENT_FEED_ADDRESS = os.getenv("AERUM_EVENT_FEED", "tcp://127.0.0.1:7000")


def init_db(db_path: str = DB_PATH) -> None:
    """Initialise the SQLite database with required tables."""

    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                t REAL,
                src TEXT,
                level TEXT,
                topic TEXT,
                payload TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS health (
                t REAL,
                src TEXT,
                status TEXT,
                details TEXT
            )
            """
        )
        conn.commit()


def _store_event(conn: sqlite3.Connection, event: Event) -> None:
    conn.execute(
        "INSERT INTO events (t, src, level, topic, payload) VALUES (?, ?, ?, ?, ?)",
        (event.timestamp, event.src, event.level, event.topic, event.to_json()),
    )


def _store_health(conn: sqlite3.Connection, health: Health) -> None:
    conn.execute(
        "INSERT INTO health (t, src, status, details) VALUES (?, ?, ?, ?)",
        (health.timestamp, health.src, health.status, health.to_json()),
    )


def _install_signal_handlers(cleanup: Callable[[], None]) -> None:
    def handler(signum, _frame):  # pragma: no cover - signal handling is best-effort
        logging.info("Received signal %s - shutting down datastore", signum)
        cleanup()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    logging.info("Starting datastore service. DB=%s feed=%s", DB_PATH, EVENT_FEED_ADDRESS)

    init_db(DB_PATH)

    ctx = zmq.Context.instance()
    sub = make_sub(
        ctx,
        EVENT_FEED_ADDRESS,
        topics=[TOPIC_EVENTS, TOPIC_HEALTH],
        bind=True,
    )

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.isolation_level = None  # autocommit mode

    def cleanup() -> None:
        logging.info("Shutting down datastore service")
        sub.close(linger=0)
        conn.close()

    _install_signal_handlers(cleanup)

    try:
        while True:
            message = sub.recv_string()
            try:
                topic, payload = message.split(" ", 1)
            except ValueError:
                logging.warning("Malformed message: %s", message)
                continue

            if topic == TOPIC_EVENTS:
                event = Event.from_json(payload)
                _store_event(conn, event)
            elif topic == TOPIC_HEALTH:
                health = Health.from_json(payload)
                _store_health(conn, health)
            else:  # pragma: no cover - guards against future unknown topics
                logging.debug("Ignoring unknown topic: %s", topic)
            conn.commit()
    finally:
        cleanup()


if __name__ == "__main__":
    main()

