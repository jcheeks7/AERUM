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
                    self.bus.send(self.name, "MissionLead", f"TASK_COMPLETE: {content}")

                elif "check_orbit" in content:
                    self.logger.log(self.name, "Checking orbital parameters...")
                    self.state["last_orbit_check"] = datetime.now().isoformat()
                    self.bus.send(self.name, "MissionLead", f"TASK_COMPLETE: {content}")
                
                elif "recalculate_trajectory" in content:
                    self.logger.log(self.name, "Recalculating trajectory using updated parameters...")
                    self.state["diagnostic_count"] += 1
                    self.bus.send(self.name, "MissionLead", f"TASK_COMPLETE: {content}")
                
                elif "analyze_thermal_data" in content:
                    self.logger.log(self.name, "Analyzing thermal data for hotspots...")
                    self.bus.send(self.name, "MissionLead", f"TASK_COMPLETE: {content}")
                
                elif "run_emergency_diagnostics" in content:
                    self.logger.log(self.name, "Emergency diagnostics in progress")
                    self.state["systems_nominal"] = False
                    self.bus.send(self.name, "MissionLead", "Emergency diagnostics complete. System compromised.")
                    self.bus.send(self.name, "MissionLead", f"TASK_COMPLETE: {content}")
                else:
                    self.logger.log(self.name, "Running standard diagnostics...")
                    self.bus.send(self.name, "MissionLead", f"TASK_COMPLETE: {content}")
            time.sleep(1)
