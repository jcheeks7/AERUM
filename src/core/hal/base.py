"""Abstract base classes for Hardware Abstraction Layer components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping


class Propulsion(ABC):
    """Abstraction for propulsion hardware control."""

    @abstractmethod
    def arm(self) -> Mapping[str, Any]:
        """Arm the propulsion system and return status details."""

    @abstractmethod
    def fire(self, duration_s: float, valve_id: str) -> Mapping[str, Any]:
        """Fire a thruster for ``duration_s`` seconds on the given valve."""

    @abstractmethod
    def disarm(self) -> Mapping[str, Any]:
        """Disarm the propulsion system."""

    @abstractmethod
    def read_sensors(self) -> Mapping[str, Any]:
        """Return the latest propulsion telemetry readings."""


class Power(ABC):
    """Abstraction for power subsystem interactions."""

    @abstractmethod
    def read_battery(self) -> Mapping[str, Any]:
        """Return current battery telemetry information."""

    @abstractmethod
    def switch(self, mode: str) -> Mapping[str, Any]:
        """Switch the power subsystem into the requested ``mode``."""
