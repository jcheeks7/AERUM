"""Dashboard service providing REST APIs and SSE for mission data."""

from __future__ import annotations

import json
import os
import queue
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, Generator, List

from flask import Flask, Response, jsonify, send_from_directory

DB_PATH = os.getenv("AERUM_DB_PATH", "aerum.db")
POLL_INTERVAL = float(os.getenv("AERUM_DASHBOARD_POLL", "1.0"))

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def _connect(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_json_field(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {"raw": value}


def _row_to_event(row: sqlite3.Row) -> Dict:
    payload = row["payload"] if "payload" in row.keys() else row[4]
    data = {
        "rowid": row["rowid"],
        "timestamp": row["t"],
        "source": row["src"],
        "level": row["level"],
        "topic": row["topic"],
        "payload": _parse_json_field(payload),
    }
    return data


def _row_to_health(row: sqlite3.Row) -> Dict:
    details = row["details"] if "details" in row.keys() else row[3]
    return {
        "timestamp": row["t"],
        "agent": row["src"],
        "status": row["status"],
        "details": _parse_json_field(details),
    }


class EventStreamer:
    """Background poller that broadcasts new events to SSE subscribers."""

    def __init__(self, db_path: str = DB_PATH, poll_interval: float = POLL_INTERVAL):
        self._db_path = db_path
        self._poll_interval = poll_interval
        self._subscribers: List[queue.Queue] = []
        self._lock = threading.Lock()
        self._last_rowid = self._get_last_rowid()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _get_last_rowid(self) -> int:
        with _connect(self._db_path) as conn:
            row = conn.execute("SELECT IFNULL(MAX(rowid), 0) AS last_id FROM events").fetchone()
            return int(row["last_id"] or 0)

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def _publish(self, event: Dict) -> None:
        with self._lock:
            for subscriber in list(self._subscribers):
                try:
                    subscriber.put_nowait(event)
                except queue.Full:  # pragma: no cover - defensive
                    # Drop the subscriber if it can't keep up.
                    self._subscribers.remove(subscriber)

    def _poll(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute(
            "SELECT rowid, t, src, level, topic, payload FROM events WHERE rowid > ? ORDER BY rowid ASC",
            (self._last_rowid,),
        ).fetchall()
        for row in rows:
            event = _row_to_event(row)
            self._last_rowid = max(self._last_rowid, event["rowid"])
            self._publish(event)

    def _run(self) -> None:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            while True:
                self._poll(conn)
                time.sleep(self._poll_interval)
        finally:  # pragma: no cover - best effort cleanup
            conn.close()


app = Flask(__name__)
streamer = EventStreamer()


@app.route("/")
def dashboard() -> Response:
    return send_from_directory(str(STATIC_DIR), "dashboard.html")


@app.route("/events")
def get_events() -> Response:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT rowid, t, src, level, topic, payload FROM events ORDER BY rowid DESC LIMIT 50"
        ).fetchall()
        events = [_row_to_event(row) for row in rows]
    return jsonify(list(reversed(events)))


@app.route("/health")
def get_health() -> Response:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT h.rowid, h.t, h.src, h.status, h.details
            FROM health h
            INNER JOIN (
                SELECT src, MAX(t) AS latest
                FROM health
                GROUP BY src
            ) latest_health ON latest_health.src = h.src AND latest_health.latest = h.t
            ORDER BY h.t DESC
            """
        ).fetchall()
        health = [_row_to_health(row) for row in rows]
    return jsonify(health)


@app.route("/missions")
def get_missions() -> Response:
    return jsonify([{"id": "demo", "status": "idle"}])


@app.route("/stream")
def stream_events() -> Response:
    def event_stream() -> Generator[str, None, None]:
        subscriber = streamer.subscribe()
        try:
            while True:
                event = subscriber.get()
                yield f"data: {json.dumps(event)}\n\n"
        except GeneratorExit:  # pragma: no cover - triggered on disconnect
            streamer.unsubscribe(subscriber)

    return Response(event_stream(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
