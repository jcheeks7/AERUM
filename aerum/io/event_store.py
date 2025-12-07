import copy
import json
import threading
from collections import deque
from datetime import datetime
from queue import Queue
from typing import Deque, Dict, Iterable, List, Optional


class EventStore:
    """Thread-safe in-memory store for timeline events and agent status."""

    def __init__(self, max_events: int = 1000):
        self._events: Deque[dict] = deque(maxlen=max_events)
        self._statuses: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._subscribers: List[Queue] = []
        self._counter = 0
        self._boot_state: Dict[str, dict] = {
            "status": "idle",
            "started_at": None,
            "completed_at": None,
            "message": None,
            "stages": [],
        }
        self._systems_state: Dict[str, dict] = {}
        self._missions_state: Dict[str, Optional[dict]] = {
            "current": None,
            "history": [],
        }

    def _next_id(self) -> int:
        with self._lock:
            self._counter += 1
            return self._counter

    def _broadcast(self, payload: dict) -> None:
        """Send payload to all active subscribers."""
        dead: List[Queue] = []
        for q in list(self._subscribers):
            try:
                q.put_nowait(payload)
            except Exception:
                dead.append(q)
        if dead:
            with self._lock:
                for q in dead:
                    if q in self._subscribers:
                        self._subscribers.remove(q)

    def record_event(
        self,
        agent: str,
        message: str,
        *,
        timestamp: Optional[datetime] = None,
        category: str = "log",
    ) -> dict:
        """Add a timeline event and update the agent's latest status."""

        ts = (timestamp or datetime.utcnow()).isoformat()
        event = {
            "id": self._next_id(),
            "timestamp": ts,
            "agent": agent,
            "message": message,
            "category": category,
        }
        with self._lock:
            self._events.append(event)
        self._broadcast({"type": "event", "event": event})
        self._update_agent_entry(agent, status=message, timestamp=ts)
        return event

    def get_events(self, *, limit: Optional[int] = None, offset: int = 0) -> List[dict]:
        """Return events ordered from latest to oldest."""

        with self._lock:
            events = list(self._events)
        events.reverse()
        if offset:
            events = events[offset:]
        if limit is not None:
            events = events[:limit]
        return events

    def get_statuses(self) -> List[dict]:
        with self._lock:
            return list(self._statuses.values())

    # ------------------------------------------------------------------
    # Agent state helpers

    def _update_agent_entry(
        self,
        agent: str,
        *,
        status: Optional[str] = None,
        timestamp: Optional[str] = None,
        health: Optional[str] = None,
    ) -> dict:
        ts = timestamp or datetime.utcnow().isoformat()
        with self._lock:
            current = copy.deepcopy(self._statuses.get(agent, {"agent": agent}))
            if status is not None:
                current["status"] = status
                current["timestamp"] = ts
            elif "timestamp" not in current:
                current["timestamp"] = ts
            if health is not None:
                current["health"] = health
            self._statuses[agent] = current
            snapshot = list(self._statuses.values())
        self._broadcast({"type": "status", "status": current})
        self._broadcast({"type": "agents", "agents": snapshot})
        return current

    def set_agent_state(
        self,
        agent: str,
        *,
        status: Optional[str] = None,
        health: Optional[str] = None,
    ) -> dict:
        return self._update_agent_entry(agent, status=status, health=health)

    # ------------------------------------------------------------------
    # Boot state helpers

    def begin_boot(self, stages: Iterable[str]) -> dict:
        now = datetime.utcnow().isoformat()
        with self._lock:
            self._boot_state = {
                "status": "running",
                "started_at": now,
                "completed_at": None,
                "message": None,
                "stages": [
                    {
                        "name": stage,
                        "status": "pending",
                        "message": None,
                        "started_at": None,
                        "completed_at": None,
                    }
                    for stage in stages
                ],
            }
            boot_copy = copy.deepcopy(self._boot_state)
        self._broadcast({"type": "boot", "boot": boot_copy})
        return boot_copy

    def _find_boot_stage(self, name: str) -> dict:
        for stage in self._boot_state.get("stages", []):
            if stage.get("name") == name:
                return stage
        stage = {
            "name": name,
            "status": "pending",
            "message": None,
            "started_at": None,
            "completed_at": None,
        }
        self._boot_state.setdefault("stages", []).append(stage)
        return stage

    def update_boot_stage(
        self,
        name: str,
        status: str,
        *,
        message: Optional[str] = None,
    ) -> dict:
        now = datetime.utcnow().isoformat()
        with self._lock:
            stage = self._find_boot_stage(name)
            stage["status"] = status
            if message is not None:
                stage["message"] = message
            if status == "running" and stage.get("started_at") is None:
                stage["started_at"] = now
            if status in {"complete", "failed"}:
                stage["completed_at"] = now
            boot_copy = copy.deepcopy(self._boot_state)
        self._broadcast({"type": "boot", "boot": boot_copy})
        return boot_copy

    def finalize_boot(self, status: str, *, message: Optional[str] = None) -> dict:
        now = datetime.utcnow().isoformat()
        with self._lock:
            self._boot_state["status"] = status
            self._boot_state["completed_at"] = now
            if message is not None:
                self._boot_state["message"] = message
            boot_copy = copy.deepcopy(self._boot_state)
        self._broadcast({"type": "boot", "boot": boot_copy})
        return boot_copy

    def reset_boot(self) -> dict:
        with self._lock:
            self._boot_state = {
                "status": "idle",
                "started_at": None,
                "completed_at": None,
                "message": None,
                "stages": [],
            }
            boot_copy = copy.deepcopy(self._boot_state)
        self._broadcast({"type": "boot", "boot": boot_copy})
        return boot_copy

    # ------------------------------------------------------------------
    # Systems telemetry

    def set_system_state(
        self,
        system: str,
        status: str,
        *,
        detail: Optional[str] = None,
    ) -> dict:
        now = datetime.utcnow().isoformat()
        with self._lock:
            entry = {
                "name": system,
                "status": status,
                "detail": detail,
                "updated_at": now,
            }
            self._systems_state[system] = entry
            systems_copy = copy.deepcopy(self._systems_state)
        self._broadcast({"type": "systems", "systems": systems_copy})
        return entry

    # ------------------------------------------------------------------
    # Mission state helpers

    def begin_mission(self, *, file: str, name: str) -> dict:
        now = datetime.utcnow().isoformat()
        with self._lock:
            current = {
                "file": file,
                "name": name,
                "status": "running",
                "started_at": now,
                "completed_at": None,
                "message": None,
                "steps": [],
            }
            self._missions_state["current"] = current
            mission_copy = copy.deepcopy(self._missions_state)
        self._broadcast({"type": "mission", "mission": mission_copy})
        return mission_copy

    def update_mission_step(
        self,
        step: str,
        status: str,
        *,
        detail: Optional[str] = None,
    ) -> Optional[dict]:
        now = datetime.utcnow().isoformat()
        with self._lock:
            current = self._missions_state.get("current")
            if not current:
                return None
            steps = current.setdefault("steps", [])
            for entry in steps:
                if entry.get("name") == step:
                    target = entry
                    break
            else:
                target = {
                    "name": step,
                    "status": "pending",
                    "detail": None,
                    "started_at": None,
                    "completed_at": None,
                }
                steps.append(target)
            target["status"] = status
            if detail is not None:
                target["detail"] = detail
            if status == "running" and target.get("started_at") is None:
                target["started_at"] = now
            if status in {"complete", "failed", "skipped"}:
                target["completed_at"] = now
            mission_copy = copy.deepcopy(self._missions_state)
        self._broadcast({"type": "mission", "mission": mission_copy})
        return target

    def update_mission_status(
        self,
        status: str,
        *,
        message: Optional[str] = None,
    ) -> Optional[dict]:
        now = datetime.utcnow().isoformat()
        with self._lock:
            current = self._missions_state.get("current")
            if not current:
                return None
            current["status"] = status
            if message is not None:
                current["message"] = message
            if status in {"complete", "failed", "aborted"}:
                current["completed_at"] = now
                history = self._missions_state.setdefault("history", [])
                history.insert(0, copy.deepcopy(current))
                self._missions_state["history"] = history[:10]
            mission_copy = copy.deepcopy(self._missions_state)
        self._broadcast({"type": "mission", "mission": mission_copy})
        return mission_copy

    # ------------------------------------------------------------------
    # Snapshot helpers

    def get_boot_state(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._boot_state)

    def get_systems_state(self) -> Dict[str, dict]:
        with self._lock:
            return copy.deepcopy(self._systems_state)

    def get_missions_state(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._missions_state)

    def get_state_snapshot(self, *, events_limit: int = 200) -> dict:
        with self._lock:
            events = list(self._events)
            events.reverse()
            if events_limit is not None:
                events = events[:events_limit]
            statuses = list(self._statuses.values())
            boot = copy.deepcopy(self._boot_state)
            systems = copy.deepcopy(self._systems_state)
            missions = copy.deepcopy(self._missions_state)
        return {
            "events": events,
            "agents": statuses,
            "boot": boot,
            "systems": systems,
            "missions": missions,
        }

    def subscribe(self) -> Queue:
        q: Queue = Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: Queue) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def to_json(self) -> str:
        with self._lock:
            payload = {
                "events": list(self._events),
                "statuses": list(self._statuses.values()),
            }
        return json.dumps(payload)


event_store = EventStore()

