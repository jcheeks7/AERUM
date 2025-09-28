import time
from datetime import datetime
from typing import Any, Dict, Tuple

from .base_agent import BaseAgent


class SpacecraftTechnician(BaseAgent):
    def __init__(self, logger, bus):
        super().__init__("SpacecraftTechnician", logger, bus)
        self.state = {
            "maintenance_tasks": 0,
            "last_task_time": None,
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
        if action == "boot_power":
            self.log("Power systems powering on...")
            self.send("MissionLead", "TASK_COMPLETE: boot_power")
        elif action == "boot_comms":
            self.log("Communications systems initializing...")
            self.send("MissionLead", "TASK_COMPLETE: boot_comms")
        elif action == "fix_power":
            self.log("Repairing power system...")
            self.send("MissionLead", "TASK_COMPLETE: fix_power")
        elif action == "fix_comms":
            self.log("Repairing communications system...")
            self.send("MissionLead", "TASK_COMPLETE: fix_comms")
        elif action.upper().startswith("REPAIR"):
            target = action.split(":", 1)[1].strip() if ":" in action else self.name
            self.log(f"Received repair command for {target}. Restoring health.")
            self.repair_health()
            self.send("MissionLead", f"TASK_COMPLETE: {action}")
        else:
            self.log("Performing system maintenance...")
            self.state["maintenance_tasks"] += 1
            self.state["last_task_time"] = datetime.now().isoformat()
            report = (
                f"Maintenance task #{self.state['maintenance_tasks']} complete at {self.state['last_task_time']}"
            )
            self.send("MissionLead", report)
            self.log(f"Sent to MissionLead: {report}")
            if action == "adjust_thrusters":
                self.log("Adjusting RCS thruster alignment...")
            elif action == "calibrate_radiators":
                self.log("Calibrating thermal radiators to optimal flow...")
            elif action == "dump_propellant":
                self.log("Emergency propellant dump initiated!")
            self.send("MissionLead", f"TASK_COMPLETE: {action}")

    def run(self):
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
            time.sleep(1)
