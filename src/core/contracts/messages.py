"""Message contract definitions for ZeroMQ-based services."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Type, TypeVar


def _default_timestamp() -> float:
    return time.time()


def _default_correlation_id() -> str:
    return str(uuid.uuid4())


T = TypeVar("T", bound="BaseMessage")


class BaseMessage:
    """Base helper for message contracts."""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls: Type[T], data: str) -> T:
        payload = json.loads(data)
        return cls(**payload)  # type: ignore[arg-type]


@dataclass(slots=True)
class Command(BaseMessage):
    src: str
    dst: str
    action: str
    payload: Dict[str, Any]
    correlation_id: str = field(default_factory=_default_correlation_id)
    timestamp: float = field(default_factory=_default_timestamp)


@dataclass(slots=True)
class Reply(BaseMessage):
    src: str
    dst: str
    status: str
    payload: Dict[str, Any]
    correlation_id: str
    timestamp: float = field(default_factory=_default_timestamp)


@dataclass(slots=True)
class Event(BaseMessage):
    src: str
    level: str
    topic: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=_default_timestamp)


@dataclass(slots=True)
class Health(BaseMessage):
    src: str
    status: str
    details: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=_default_timestamp)

