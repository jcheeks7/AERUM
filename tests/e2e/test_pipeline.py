from __future__ import annotations

import importlib
import os
import socket
import sqlite3
import time
from multiprocessing import Process
from typing import Dict

import pytest

zmq = pytest.importorskip("zmq")

from core.contracts import Command, Reply
from core.ipc import make_req


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.timeout(30)
def test_pipeline(tmp_path) -> None:
    event_port = _get_free_port()
    mission_lead_port = _get_free_port()
    technician_port = _get_free_port()

    db_path = tmp_path / "aerum.db"

    env_updates: Dict[str, str] = {
        "AERUM_DB_PATH": str(db_path),
        "AERUM_EVENT_FEED": f"tcp://127.0.0.1:{event_port}",
        "MISSION_LEAD_COMMAND_ADDR": f"tcp://127.0.0.1:{mission_lead_port}",
        "MISSION_LEAD_CLIENT_ADDR": f"tcp://127.0.0.1:{mission_lead_port}",
        "TECHNICIAN_COMMAND_ADDR": f"tcp://127.0.0.1:{technician_port}",
    }

    original_env = {key: os.environ.get(key) for key in env_updates}
    os.environ.update(env_updates)

    processes: list[Process] = []

    try:
        datastore_module = importlib.reload(importlib.import_module("services.datastore.main"))
        mission_lead_module = importlib.reload(importlib.import_module("services.mission_lead.main"))
        technician_module = importlib.reload(importlib.import_module("services.technician.main"))

        def start(target, name: str) -> None:
            proc = Process(target=target, name=name)
            proc.start()
            processes.append(proc)

        start(datastore_module.main, "datastore")
        time.sleep(0.5)
        start(mission_lead_module.main, "mission_lead")
        start(technician_module.main, "technician")

        time.sleep(1.0)

        ctx = zmq.Context.instance()
        socket = make_req(ctx, env_updates["MISSION_LEAD_CLIENT_ADDR"])
        reply: Reply | None = None
        try:
            command = Command(
                src="test_harness",
                dst="mission_lead",
                action="delegate",
                payload={"target": "technician", "action": "noop", "payload": {}},
            )
            socket.send_string(command.to_json())
            reply = Reply.from_json(socket.recv_string())
        finally:
            socket.close(linger=0)

        assert reply is not None
        assert reply.status == "ok"
        delegated = reply.payload.get("delegate")
        assert delegated["src"] == "technician"
        assert delegated["status"] == "ok"

        time.sleep(1.5)

        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            events = conn.execute("SELECT src, topic, payload FROM events").fetchall()
            health = conn.execute("SELECT src, status, details FROM health").fetchall()

        event_sources = {row["src"] for row in events}
        assert {"mission_lead", "technician"}.issubset(event_sources)

        health_sources = {row["src"] for row in health}
        assert {"mission_lead", "technician"}.issubset(health_sources)

    finally:
        for proc in processes:
            if proc.is_alive():
                proc.terminate()
        for proc in processes:
            proc.join(timeout=2)

        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

