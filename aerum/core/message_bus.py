"""Simple in-memory message bus used by agents to communicate."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
from typing import Deque, Dict, List


class MessageBus:
    """Thread-safe-ish queueing layer for intra-crew traffic."""

    def __init__(self) -> None:
        self._queues: Dict[str, Deque[dict]] = defaultdict(deque)

    def register_agent(self, agent_name: str) -> None:
        self._queues.setdefault(agent_name, deque())

    def send(self, sender: str, recipient: str, content) -> None:
        payload = {
            "from": sender,
            "to": recipient,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._queues[recipient].append(payload)

    def broadcast(self, sender: str, content) -> None:
        for recipient in list(self._queues.keys()):
            self.send(sender, recipient, content)

    def fetch(self, agent_name: str) -> List[dict]:
        queue = self._queues.get(agent_name, deque())
        messages = list(queue)
        queue.clear()
        return messages
