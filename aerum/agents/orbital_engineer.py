import time
from datetime import datetime
from typing import Any, Dict, Tuple

from .base_agent import BaseAgent


class OrbitalEngineer(BaseAgent):
    def __init__(self, logger, bus):
        super().__init__("OrbitalEngineer", logger, bus)
        self.state = {
            "last_anomaly": None,
            "diagnostic_count": 0,
            "systems_nominal": True,
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
        if "Anomaly" in action:
            self.log("Initiating anomaly diagnostic protocol")
            time.sleep(1)
            self.state["last_anomaly"] = datetime.now().isoformat()
            self.state["diagnostic_count"] += 1
            self.state["systems_nominal"] = True
            report = (
                f"Diagnostics complete. Count: {self.state['diagnostic_count']}. Systems nominal."
            )
            self.send("MissionLead", report)
            self.log(f"Sent to MissionLead: {report}")
            self.send("MissionLead", f"TASK_COMPLETE: {action}")
        elif action == "check_orbit":
            self.log("Checking orbital parameters...")
            self.state["last_orbit_check"] = datetime.now().isoformat()
            self.send("MissionLead", f"TASK_COMPLETE: {action}")
        elif action == "recalculate_trajectory":
            self.log("Recalculating trajectory using updated parameters...")
            self.state["diagnostic_count"] += 1
            self.send("MissionLead", f"TASK_COMPLETE: {action}")
        elif action == "analyze_thermal_data":
            self.log("Analyzing thermal data for hotspots...")
            self.send("MissionLead", f"TASK_COMPLETE: {action}")
        elif action == "run_emergency_diagnostics":
            self.log("Emergency diagnostics in progress")
            self.state["systems_nominal"] = False
            self.send(
                "MissionLead",
                "Emergency diagnostics complete. System compromised.",
            )
            self.send("MissionLead", f"TASK_COMPLETE: {action}")
        else:
            self.log("Running standard diagnostics...")
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
