from __future__ import annotations

import importlib
import json
import os
import socket
import sqlite3
import time
from multiprocessing import Process
from typing import Dict, List

import pytest

zmq = pytest.importorskip("zmq")

from core.contracts import Command, Reply
from core.ipc import make_req


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _run_test_technician() -> None:
    from services.technician.main import TechnicianService
    from core.hal.adapters.propulsion_mock import PropulsionMock

    class DeterministicPropulsion(PropulsionMock):
        def __init__(self) -> None:
            super().__init__()
            self._pressures: List[float] = [45.0, 15.0]

        def fire(self, duration_s: float, valve_id: str) -> Dict[str, float | str]:
            if self._pressures:
                pressure = self._pressures.pop(0)
            else:
                pressure = 15.0
            telemetry: Dict[str, float | str] = {
                "prop_pressure": pressure,
                "valve_id": valve_id,
                "duration_s": duration_s,
            }
            self._last_telemetry.update(telemetry)
            return telemetry

    TechnicianService(propulsion=DeterministicPropulsion()).run()


@pytest.mark.timeout(45)
def test_fault_detection_and_hal(tmp_path) -> None:
    event_port = _get_free_port()
    mission_lead_port = _get_free_port()
    technician_port = _get_free_port()
    fault_port = _get_free_port()

    db_path = tmp_path / "aerum_fault.db"

    env_updates = {
        "AERUM_DB_PATH": str(db_path),
        "AERUM_EVENT_FEED": f"tcp://127.0.0.1:{event_port}",
        "MISSION_LEAD_COMMAND_ADDR": f"tcp://127.0.0.1:{mission_lead_port}",
        "MISSION_LEAD_CLIENT_ADDR": f"tcp://127.0.0.1:{mission_lead_port}",
        "TECHNICIAN_COMMAND_ADDR": f"tcp://127.0.0.1:{technician_port}",
        "FAULT_ANALYST_COMMAND_ADDR": f"tcp://127.0.0.1:{fault_port}",
    }

    original_env = {key: os.environ.get(key) for key in env_updates}
    os.environ.update(env_updates)

    processes: list[Process] = []

    try:
        datastore_module = importlib.reload(importlib.import_module("services.datastore.main"))
        mission_lead_module = importlib.reload(importlib.import_module("services.mission_lead.main"))
        fault_module = importlib.reload(importlib.import_module("services.fault_analyst.main"))

        def start(target, name: str) -> None:
            proc = Process(target=target, name=name)
            proc.start()
            processes.append(proc)

        start(datastore_module.main, "datastore")
        time.sleep(0.5)
        start(mission_lead_module.main, "mission_lead")
        start(_run_test_technician, "technician")
        start(fault_module.main, "fault_analyst")

        time.sleep(1.0)

        ctx = zmq.Context.instance()
        socket = make_req(ctx, env_updates["MISSION_LEAD_CLIENT_ADDR"])
        try:
            arm_command = Command(
                src="test_harness",
                dst="mission_lead",
                action="delegate",
                payload={"target": "technician", "action": "arm_propulsion", "payload": {}},
            )
            socket.send_string(arm_command.to_json())
            arm_reply = Reply.from_json(socket.recv_string())
            assert arm_reply.status == "ok"

            fire_command = Command(
                src="test_harness",
                dst="mission_lead",
                action="delegate",
                payload={
                    "target": "technician",
                    "action": "fire_thruster",
                    "payload": {"duration_s": 1.0, "valve_id": "A"},
                },
            )
            socket.send_string(fire_command.to_json())
            fire_reply = Reply.from_json(socket.recv_string())

            fire_low_command = Command(
                src="test_harness",
                dst="mission_lead",
                action="delegate",
                payload={
                    "target": "technician",
                    "action": "fire_thruster",
                    "payload": {"duration_s": 0.5, "valve_id": "B"},
                },
            )
            socket.send_string(fire_low_command.to_json())
            fire_low_reply = Reply.from_json(socket.recv_string())
        finally:
            socket.close(linger=0)

        assert fire_reply.status == "ok"
        assert fire_low_reply.status == "ok"
        assert "telemetry" in fire_reply.payload.get("delegate", {})
        low_pressure = (
            fire_low_reply.payload.get("delegate", {})
            .get("payload", {})
            .get("telemetry", {})
            .get("prop_pressure")
        )
        assert isinstance(low_pressure, (int, float)) and low_pressure < 20.0

        time.sleep(2.0)

        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            telemetry_rows = conn.execute(
                "SELECT payload FROM events WHERE topic = ?", ("telemetry.propulsion",)
            ).fetchall()
            alarm_rows = conn.execute(
                "SELECT payload, level FROM events WHERE topic = ?", ("fdir.alarm",)
            ).fetchall()

        assert telemetry_rows, "Expected propulsion telemetry events"
        telemetry_payloads = [json.loads(row["payload"]) for row in telemetry_rows]
        assert any(
            payload["payload"].get("prop_pressure") is not None for payload in telemetry_payloads
        )

        assert alarm_rows, "Expected FDIR alarm events"
        alarm_payloads = [json.loads(row["payload"]) for row in alarm_rows]
        assert any(
            alarm["payload"].get("code") == "PROP_PRESSURE_LOW" and alarm["level"] == "ALARM"
            for alarm in alarm_payloads
        )

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
