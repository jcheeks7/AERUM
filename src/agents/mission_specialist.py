import time
from typing import Any, Dict, Tuple

from .base_agent import BaseAgent


class MissionSpecialist(BaseAgent):
    def __init__(self, logger, bus):
        super().__init__("MissionSpecialist", logger, bus)
        self.state = {
            "scans_completed": 0,
            "anomalies_found": 0,
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
        if action == "scan_environment":
            self.log("Analyzing mission data...")
            time.sleep(1)
            self.state["scans_completed"] += 1
            self.state["anomalies_found"] += 1
            self.log("Anomaly detected in scan results")
            self.send("OrbitalEngineer", "Anomaly detected in scan results")
            self.send(
                "MissionLead",
                "Scan complete. Anomaly forwarded to engineering.",
            )
            self.log(
                f"Sent report: {self.state['anomalies_found']} anomalies found across {self.state['scans_completed']} scans"
            )
            self.send("MissionLead", f"TASK_COMPLETE: {action}")
        elif action == "run_thermal_scan":
            self.log("Running high-resolution thermal scan...")
            time.sleep(1)
            self.state["anomalies_found"] += 1
            self.send("OrbitalEngineer", "Thermal anomaly detected.")
            self.log("Sent to OrbitalEngineer: Thermal anomaly detected.")
            self.send("MissionLead", f"TASK_COMPLETE: {action}")
        elif action == "prepare_data_dump":
            self.log("Packaging and encrypting mission data for uplink...")
            self.send("MissionLead", "Data uplink ready.")
            self.send("MissionLead", f"TASK_COMPLETE: {action}")
        else:
            self.log(f"No handler defined for action {action}")
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
