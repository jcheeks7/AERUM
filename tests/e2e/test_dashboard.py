import importlib
import json
import os
import sqlite3
import sys
import time
from multiprocessing import Process
from pathlib import Path
from typing import Dict, List
from urllib import request

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"

for path in (PROJECT_ROOT, SRC_ROOT):
    str_path = str(path)
    if str_path not in sys.path:
        sys.path.insert(0, str_path)

pytest.importorskip("zmq")


def test_dashboard_rest_endpoints(tmp_path) -> None:
    db_path = tmp_path / "aerum.db"
    dashboard_port = _get_free_port()

    env_updates: Dict[str, str] = {
        "AERUM_DB_PATH": str(db_path),
    }

    original_env = {key: os.environ.get(key) for key in env_updates}
    os.environ.update(env_updates)

    processes: List[Process] = []

    try:
        datastore_module = importlib.reload(importlib.import_module("services.datastore.main"))
        dashboard_module = importlib.reload(importlib.import_module("services.dashboard.app"))

        datastore_module.init_db(str(db_path))

        _start_process(datastore_module.main, processes, name="datastore")
        time.sleep(0.5)
        _start_process(
            dashboard_module.app.run,
            processes,
            name="dashboard",
            kwargs={"host": "127.0.0.1", "port": dashboard_port, "debug": False, "use_reloader": False},
        )

        _wait_for_http(f"http://127.0.0.1:{dashboard_port}/health")

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO events (t, src, level, topic, payload) VALUES (?, ?, ?, ?, ?)",
                (time.time(), "test_harness", "INFO", "demo", json.dumps({"message": "hello"})),
            )
            conn.commit()

        events = _fetch_json(f"http://127.0.0.1:{dashboard_port}/events")
        assert any(event.get("source") == "test_harness" for event in events)

        health = _fetch_json(f"http://127.0.0.1:{dashboard_port}/health")
        assert isinstance(health, list)

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


def _start_process(target, processes: List[Process], name: str, kwargs: Dict | None = None) -> None:
    proc = Process(target=target, name=name, kwargs=kwargs or {})
    proc.start()
    processes.append(proc)


def _wait_for_http(url: str, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with request.urlopen(url, timeout=1):
                return
        except Exception:  # pragma: no cover - best effort wait
            time.sleep(0.1)
    raise TimeoutError(f"Timed out waiting for {url}")


def _fetch_json(url: str):
    with request.urlopen(url, timeout=5) as response:
        data = response.read().decode("utf-8")
    return json.loads(data)


def _get_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
