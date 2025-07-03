import time

class MissionSpecialist:
    def __init__(self, logger, bus):
        self.name = "MissionSpecialist"
        self.logger = logger
        self.bus = bus

    def run(self):
        while True:
            messages = self.bus.fetch(self.name)
            for msg in messages:
                self.logger.log(self.name, f"Received from {msg['from']}: {msg['content']}")
                self.logger.log(self.name, "Analyzing mission data...")

                # Simulate finding an anomaly
                if "scan_environment" in msg["content"]:
                    time.sleep(1)
                    self.logger.log(self.name, "⚠️ Anomaly detected in scan results")
                    self.bus.send(self.name, "OrbitalEngineer", "Anomaly detected in scan results")
                    self.bus.send(self.name, "MissionLead", "Scan complete. Anomaly forwarded to engineering.")
            time.sleep(1)
