import json
import threading
from collections import deque
from datetime import datetime
from queue import Queue
from typing import Deque, Dict, List, Optional


class EventStore:
    """Thread-safe in-memory store for timeline events and agent status."""

    def __init__(self, max_events: int = 1000):
        self._events: Deque[dict] = deque(maxlen=max_events)
        self._statuses: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._subscribers: List[Queue] = []
        self._counter = 0

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
            self._statuses[agent] = {
                "agent": agent,
                "status": message,
                "timestamp": ts,
            }
        self._broadcast({"type": "event", "event": event})
        self._broadcast(
            {
                "type": "status",
                "status": self._statuses[agent],
            }
        )
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

