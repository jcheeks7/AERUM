"""Entry point to launch the service-oriented AERUM stack."""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from multiprocessing import Process
from typing import Callable, List, Optional

import zmq

from src.core.contracts import Command, Reply
from src.core.ipc import make_req
from src.services.datastore.main import main as datastore_main
from src.services.mission_lead.main import main as mission_lead_main
from src.services.technician.main import main as technician_main

MISSION_LEAD_CLIENT_ADDRESS = os.getenv("MISSION_LEAD_CLIENT_ADDR", "tcp://127.0.0.1:5001")


def _start_process(target: Callable[[], None], name: str) -> Process:
    process = Process(target=target, name=name, daemon=False)
    process.start()
    logging.info("Started %s (pid=%s)", name, process.pid)
    return process


def _send_demo_command() -> None:
    ctx = zmq.Context.instance()
    socket = make_req(ctx, MISSION_LEAD_CLIENT_ADDRESS)
    try:
        command = Command(
            src="demo",
            dst="mission_lead",
            action="delegate",
            payload={"target": "technician", "action": "noop", "payload": {}},
        )
        socket.send_string(command.to_json())
        reply = Reply.from_json(socket.recv_string())
        logging.info("Demo delegate reply: %s", reply.payload)
    finally:
        socket.close(linger=0)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")

    processes: List[Process] = []
    dashboard_proc: Optional[subprocess.Popen[str]] = None

    def shutdown(_signum: int, _frame) -> None:
        logging.info("Shutting down service stack")
        for proc in processes:
            if proc.is_alive():
                proc.terminate()
        for proc in processes:
            proc.join(timeout=2)
        if dashboard_proc and dashboard_proc.poll() is None:
            dashboard_proc.terminate()
            try:
                dashboard_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                dashboard_proc.kill()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    processes.append(_start_process(datastore_main, "datastore"))
    # Give datastore time to bind the SUB socket before publishers connect.
    time.sleep(0.5)
    processes.append(_start_process(mission_lead_main, "mission_lead"))
    processes.append(_start_process(technician_main, "technician"))

    if os.getenv("AERUM_NO_DASHBOARD"):
        logging.info("Dashboard service launch skipped (AERUM_NO_DASHBOARD set)")
    else:
        dashboard_cmd = [sys.executable, "-m", "src.services.dashboard.app"]
        try:
            dashboard_proc = subprocess.Popen(dashboard_cmd)
        except OSError as exc:
            logging.error("Failed to launch dashboard service: %s", exc)
        else:
            logging.info("Dashboard service running at http://localhost:5000")

    time.sleep(1.0)
    try:
        _send_demo_command()
    except Exception as exc:  # pragma: no cover - demo best effort
        logging.error("Demo command failed: %s", exc)

    logging.info("Service stack running. Press Ctrl+C to exit.")
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()

