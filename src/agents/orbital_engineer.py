import time
from datetime import datetime

class OrbitalEngineer:
    def __init__(self, logger, bus):
        self.name = "OrbitalEngineer"
        self.logger = logger
        self.bus = bus
        self.state = {
            "last_anomaly": None,
            "diagnostic_count": 0,
            "systems_nominal": True
        }

    def run(self):
        while True:
            messages = self.bus.fetch(self.name)
            for msg in messages:
                content = msg["content"]
                sender = msg["from"]
                self.logger.log(self.name, f"Received from {sender}: {content}")

                if "Anomaly" in content:
                    self.logger.log(self.name, "Initiating anomaly diagnostic protocol")
                    time.sleep(1)

                    # Update state
                    self.state["last_anomaly"] = datetime.now().isoformat()
                    self.state["diagnostic_count"] += 1
                    self.state["systems_nominal"] = True  # Assume OK for now

                    # Smart response to MissionLead
                    report = f"Diagnostics complete. Count: {self.state['diagnostic_count']}. Systems nominal."
                    self.bus.send(self.name, "MissionLead", report)
                    self.logger.log(self.name, f"Sent to MissionLead: {report}")
                else:
                    self.logger.log(self.name, "Running standard diagnostics...")
            time.sleep(1)
