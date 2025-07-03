import time

class OrbitalEngineer:
    def __init__(self, logger, bus):
        self.name = "OrbitalEngineer"
        self.logger = logger
        self.bus = bus

    def run(self):
        while True:
            messages = self.bus.fetch(self.name)
            for msg in messages:
                self.logger.log(self.name, f"Received from {msg['from']}: {msg['content']}")
                if "Anomaly" in msg["content"]:
                    self.logger.log(self.name, "⚙️ Initiating anomaly diagnostic protocol")
                    time.sleep(1)
                    self.bus.send(self.name, "MissionLead", "Diagnostics complete. Report: No critical issues.")
                else:
                    self.logger.log(self.name, "Running standard diagnostics...")
            time.sleep(1)
