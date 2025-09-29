import time
from typing import Any, Dict, Tuple

from .base_agent import BaseAgent
from interface.event_store import event_store


class MonitoringAgent(BaseAgent):
    def __init__(self, logger, bus, interval=1):
        super().__init__("SystemMonitor", logger, bus)
        self.interval = interval
        self.state = {
            "systems": {
                "power_ok": True,
                "comms_ok": True,
                "o2_ok": True,
            },
            "boot_pending": {
                "power": True,
                "comms": True,
            },
        }

    def _extract_action(self, content: Any) -> Tuple[str, Dict[str, Any]]:
        if isinstance(content, dict):
            metadata = content.copy()
            action = metadata.get("action")
        else:
            action = str(content)
            metadata = {"action": action}
        metadata.setdefault("retries", 1)
        metadata.setdefault("retry_delay", 0.5)
        return action, metadata

    def _perform_action(self, action: str) -> None:
        systems = self.state["systems"]
        if action == "boot_power":
            if systems["power_ok"]:
                self.log("Verifying power system startup...")
                self.state["boot_pending"]["power"] = False
                self.send("MissionLead", "TASK_COMPLETE: boot_power")
                event_store.set_system_state("power", "nominal", detail="Power verified by monitoring")
            else:
                self.log("Power system failure detected during boot")
                self.send("MissionLead", "SYSTEM_FAILURE: power")
                raise RuntimeError("Power system verification failed")
        elif action == "boot_comms":
            if systems["comms_ok"]:
                self.log("Verifying communications system startup...")
                self.state["boot_pending"]["comms"] = False
                self.send("MissionLead", "TASK_COMPLETE: boot_comms")
                event_store.set_system_state("comms", "nominal", detail="Comms verified by monitoring")
            else:
                self.log("Communications failure detected during boot")
                self.send("MissionLead", "SYSTEM_FAILURE: comms")
                raise RuntimeError("Communications verification failed")
        elif action == "fix_power":
            self.log("Power system repaired, resetting status...")
            systems["power_ok"] = True
            self.send("MissionLead", "TASK_COMPLETE: fix_power")
            event_store.set_system_state("power", "nominal", detail="Power system nominal")
        elif action == "fix_comms":
            self.log("Communications system repaired, resetting status...")
            systems["comms_ok"] = True
            self.send("MissionLead", "TASK_COMPLETE: fix_comms")
            event_store.set_system_state("comms", "nominal", detail="Communications nominal")
        else:
            self.log(f"No monitoring handler defined for {action}")
            self.send("MissionLead", f"TASK_COMPLETE: {action}")

    def _monitor_systems(self):
        systems = self.state["systems"]
        boot_pending = self.state["boot_pending"]
        if any(boot_pending.values()):
            return
        if not systems["power_ok"]:
            self.log("Power system failure detected")
            self.send("MissionLead", "SYSTEM_FAILURE: power")
            event_store.set_system_state("power", "fault", detail="Power system failure detected")
        if not systems["comms_ok"]:
            self.log("Communications failure detected")
            self.send("MissionLead", "SYSTEM_FAILURE: comms")
            event_store.set_system_state("comms", "fault", detail="Comms failure detected")
        if systems.get("o2_ok"):
            event_store.set_system_state("o2", "nominal", detail="Life support stable")
        else:
            event_store.set_system_state("o2", "fault", detail="Life support anomaly")

    def run(self):
        event_store.set_agent_state(self.name, status="Monitoring systems")
        while True:
            messages = self.bus.fetch(self.name)
            for msg in messages:
                content = msg["content"]
                sender = msg["from"]
                self.log(f"Received from {sender}: {content}")
                action, metadata = self._extract_action(content)
                if not action:
                    continue
                self.execute_with_resilience(
                    action,
                    lambda action_name=action: self._perform_action(action_name),
                    conditions=metadata.get("conditions"),
                    retries=metadata.get("retries", 1),
                    timeout=metadata.get("timeout"),
                    retry_delay=metadata.get("retry_delay", 0.5),
                )

            self._monitor_systems()
            time.sleep(self.interval)
