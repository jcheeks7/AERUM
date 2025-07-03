import time

class MissionSpecialist:
    def __init__(self, logger, bus):
        self.name = "MissionSpecialist"
        self.logger = logger
        self.bus = bus
        self.state = {
            "scans_completed": 0,
            "anomalies_found": 0
        }

    def run(self):
        while True:
            messages = self.bus.fetch(self.name)
            for msg in messages:
                content = msg["content"]
                sender = msg["from"]
                self.logger.log(self.name, f"Received from {sender}: {content}")
                self.logger.log(self.name, "Analyzing mission data...")

                if "scan_environment" in content:
                    time.sleep(1)
                    self.state["scans_completed"] += 1
                    self.state["anomalies_found"] += 1

                    self.logger.log(self.name, "Anomaly detected in scan results")
                    self.bus.send(self.name, "OrbitalEngineer", "Anomaly detected in scan results")
                    self.bus.send(self.name, "MissionLead", "Scan complete. Anomaly forwarded to engineering.")
                    self.logger.log(self.name, f"Sent report: {self.state['anomalies_found']} anomalies found across {self.state['scans_completed']} scans")
            time.sleep(1)
                elif "run_thermal_scan" in content:
                    self.logger.log(self.name, "Running high-resolution thermal scan...")
                    time.sleep(1)
                    self.state["anomalies_found"] += 1
                    self.bus.send(self.name, "OrbitalEngineer", "Thermal anomaly detected.")
                    self.logger.log(self.name, f"Sent to OrbitalEngineer: Thermal anomaly detected.")
                
                elif "prepare_data_dump" in content:
                    self.logger.log(self.name, "Packaging and encrypting mission data for uplink...")
                    self.bus.send(self.name, "MissionLead", "Data uplink ready.")
