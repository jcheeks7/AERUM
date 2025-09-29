"""Runtime controller orchestrating boot and mission lifecycle."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from agents.mission_lead import MissionLead
from agents.mission_specialist import MissionSpecialist
from agents.monitoring_agent import MonitoringAgent
from agents.orbital_engineer import OrbitalEngineer
from agents.spacecraft_technician import SpacecraftTechnician
from interface.event_store import EventStore, event_store
from utils.logger import Logger
from utils.message_bus import MessageBus


def wrap_logger_for_ui(logger: Logger, store: EventStore = event_store) -> None:
    """Proxy the logger so log lines are mirrored into the UI event store."""

    original_log = logger.log

    def ui_log(agent: str, message: str) -> None:
        original_log(agent, message)
        store.record_event(agent, message)

    logger.log = ui_log  # type: ignore[assignment]


class RuntimeController:
    """Coordinates background agents, boot sequencing, and mission execution."""

    def __init__(self, *, store: Optional[EventStore] = None) -> None:
        self.store = store or event_store
        self.logger = Logger()
        wrap_logger_for_ui(self.logger, self.store)
        self.bus = MessageBus()

        self._boot_lock = threading.Lock()
        self._mission_lock = threading.Lock()
        self._boot_thread: Optional[threading.Thread] = None
        self._mission_thread: Optional[threading.Thread] = None
        self._boot_complete = threading.Event()
        self._mission_agents_started = False

        self._technician = SpacecraftTechnician(self.logger, self.bus)
        self._monitor = MonitoringAgent(self.logger, self.bus)
        self._mission_lead: Optional[MissionLead] = None
        self._engineer: Optional[OrbitalEngineer] = None
        self._specialist: Optional[MissionSpecialist] = None

        self._background_threads: List[threading.Thread] = []
        self._start_background_agent(self._technician.run, "SpacecraftTechnician")
        self._start_background_agent(self._monitor.run, "SystemMonitor")

    # ------------------------------------------------------------------
    # Public API

    def list_missions(self) -> List[Dict[str, str]]:
        missions: List[Dict[str, str]] = []
        missions_dir = Path("missions")
        for path in sorted(missions_dir.glob("*.json")):
            name = path.stem.replace("_", " ")
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                name = data.get("name") or name
            except Exception:
                pass
            missions.append({"file": path.name, "name": name})
        return missions

    def get_state_snapshot(self) -> dict:
        return self.store.get_state_snapshot()

    def start_boot(self) -> Tuple[bool, Optional[str]]:
        with self._boot_lock:
            boot_state = self.store.get_boot_state()
            if boot_state.get("status") == "running":
                return False, "Boot sequence already running"
            if boot_state.get("status") == "complete":
                return False, "Boot sequence already complete"
            self.store.reset_boot()
            self._boot_complete.clear()
            self._boot_thread = threading.Thread(target=self._boot_worker, daemon=True)
            self._boot_thread.start()
        return True, None

    def start_mission(self, mission_file: str) -> Tuple[bool, Optional[str]]:
        missions_dir = Path("missions")
        mission_path = missions_dir / mission_file
        if not mission_path.exists():
            return False, "Mission file not found"
        if not self._boot_complete.is_set():
            return False, "Boot sequence must complete before launching a mission"
        with self._mission_lock:
            if self._mission_thread and self._mission_thread.is_alive():
                return False, "A mission is already in progress"
            if not self._mission_agents_started:
                self._start_mission_agents()

            mission_name = mission_path.stem.replace("_", " ")
            try:
                data = json.loads(mission_path.read_text(encoding="utf-8"))
                mission_name = data.get("name") or mission_name
            except Exception:
                pass

            self.store.begin_mission(file=mission_path.name, name=mission_name)

            self._mission_thread = threading.Thread(
                target=self._mission_worker,
                args=(mission_path.name,),
                daemon=True,
            )
            self._mission_thread.start()
        return True, None

    # ------------------------------------------------------------------
    # Internal helpers

    def _start_background_agent(self, target, agent_name: str) -> None:
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        self._background_threads.append(thread)
        self.store.set_agent_state(agent_name, status="Online")

    def _start_mission_agents(self) -> None:
        self._engineer = OrbitalEngineer(self.logger, self.bus)
        self._specialist = MissionSpecialist(self.logger, self.bus)
        self._mission_lead = MissionLead(self.logger, self.bus)

        self._start_background_agent(self._engineer.run, "OrbitalEngineer")
        self._start_background_agent(self._specialist.run, "MissionSpecialist")
        self.store.set_agent_state("MissionLead", status="Ready for missions")
        self._mission_agents_started = True

    def _mission_worker(self, mission_file: str) -> None:
        assert self._mission_lead is not None
        try:
            self._mission_lead.run(mission_file)
            missions_state = self.store.get_missions_state()
            current = missions_state.get("current")
            if current and current.get("status") == "running":
                self.store.update_mission_status("complete", message="Mission finished")
        except Exception as exc:  # pragma: no cover - runtime safety
            self.logger.log("MissionLead", f"Mission execution crashed: {exc}")
            self.store.update_mission_status("failed", message=str(exc))

    def _boot_worker(self) -> None:
        stages = ["power", "comms"]
        required_agents = ["SpacecraftTechnician", "SystemMonitor"]
        timeout = 5

        self.store.begin_boot(stages)
        for system in stages:
            self.store.set_system_state(system, "pending", detail="Awaiting boot")
        self.store.set_agent_state("MissionLead", status="Coordinating boot")

        success = True
        for system in stages:
            action = f"boot_{system}"
            while self.bus.fetch("MissionLead"):
                pass  # Drain inbox from previous stage
            self.logger.log("MissionLead", f"Action: {action}")
            self.store.update_boot_stage(system, "running", message=f"Booting {system}")
            for agent_name in required_agents:
                self.bus.send("MissionLead", agent_name, action)

            start = time.time()
            acknowledged = set()
            failure_reason: Optional[str] = None

            while time.time() - start < timeout and acknowledged != set(required_agents):
                messages = self.bus.fetch("MissionLead")
                for message in messages:
                    sender = message.get("from")
                    content = message.get("content", "")
                    if isinstance(content, str) and content == f"TASK_COMPLETE: {action}":
                        acknowledged.add(sender)
                        self.logger.log("MissionLead", f"Acknowledged {action} by {sender}")
                    elif isinstance(content, str) and content.startswith("FAILURE:"):
                        payload = content.split("FAILURE:", 1)[1].strip()
                        failure_action, _, reason = payload.partition("|")
                        failure_action = failure_action.strip()
                        reason = reason.strip() or "Agent reported failure"
                        self.logger.log(
                            "MissionLead",
                            f"Failure reported by {sender} for {failure_action}: {reason}",
                        )
                        if failure_action == action:
                            acknowledged.discard(sender)
                            failure_reason = reason
                            self.store.update_boot_stage(
                                system,
                                "failed",
                                message=f"Failure reported: {reason}",
                            )
                            break
                    elif isinstance(content, str) and content.startswith("SYSTEM_FAILURE:"):
                        failure_type = content.split(":", 1)[1].strip()
                        self.logger.log(
                            "MissionLead",
                            f"Boot failure detected: {failure_type}",
                        )
                        failure_reason = f"System failure: {failure_type}"
                        self.store.update_boot_stage(
                            system,
                            "failed",
                            message=failure_reason,
                        )
                        self.store.set_system_state(
                            failure_type,
                            "fault",
                            detail="Failure detected during boot",
                        )
                        break
                if failure_reason:
                    break
                time.sleep(0.1)

            if acknowledged != set(required_agents):
                missing = set(required_agents) - acknowledged
                failure_reason = failure_reason or f"Missing acknowledgements: {', '.join(missing)}"
                self.logger.log(
                    "MissionLead",
                    f"Boot incomplete. Missing acknowledgements from: {', '.join(missing)}",
                )
                self.store.update_boot_stage(
                    system,
                    "failed",
                    message=failure_reason,
                )
                self.store.set_system_state(system, "fault", detail=failure_reason)
                success = False
                break

            self.logger.log("MissionLead", f"{system.title()} subsystem boot confirmed.")
            self.store.update_boot_stage(system, "complete", message="Subsystem nominal")
            self.store.set_system_state(system, "nominal", detail="Subsystem nominal")

        if success:
            self.logger.log("MissionLead", "All systems nominal.")
            self.store.finalize_boot("complete", message="All systems nominal")
            self.store.set_agent_state("MissionLead", status="Boot complete")
            self._boot_complete.set()
        else:
            self.store.finalize_boot("failed", message="Boot sequence failed")
            self.store.set_agent_state("MissionLead", status="Boot failed")
