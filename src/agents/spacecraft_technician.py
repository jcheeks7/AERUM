import time
from datetime import datetime

class SpacecraftTechnician:
    def __init__(self, logger, bus):
        self.name = "SpacecraftTechnician"
        self.logger = logger
        self.bus = bus
        self.state = {
            "maintenance_tasks": 0,
            "last_task_time": None
        }

    def run(self):
        while True:
            messages = self.bus.fetch(self.name)
            for msg in messages:
                content = msg["content"]
                sender = msg["from"]
                self.logger.log(self.name, f"Received from {sender}: {content}")
                self.logger.log(self.name, "Performing system maintenance...")

                self.state["maintenance_tasks"] += 1
                self.state["last_task_time"] = datetime.now().isoformat()

                report = f"Maintenance task #{self.state['maintenance_tasks']} complete at {self.state['last_task_time']}"
                self.bus.send(self.name, "MissionLead", report)
                self.logger.log(self.name, f"Sent to MissionLead: {report}")
                if "adjust_thrusters" in content:
                    self.logger.log(self.name, "Adjusting RCS thruster alignment...")
                    self.bus.send(self.name, "MissionLead", f"TASK_COMPLETE: {content}")

                elif "calibrate_radiators" in content:
                    self.logger.log(self.name, "Calibrating thermal radiators to optimal flow...")
                    self.bus.send(self.name, "MissionLead", f"TASK_COMPLETE: {content}")

                elif "dump_propellant" in content:
                    self.logger.log(self.name, "Emergency propellant dump initiated!")
                    self.bus.send(self.name, "MissionLead", "Propellant dump complete.")
                    self.bus.send(self.name, "MissionLead", f"TASK_COMPLETE: {content}")
            
            time.sleep(1)
