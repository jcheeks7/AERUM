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

                # Handle boot actions
                if content == "boot_power":
                    self.logger.log(self.name, "Power systems powering on...")
                    self.bus.send(self.name, "MissionLead", "TASK_COMPLETE: boot_power")
                    continue
                if content == "boot_comms":
                    self.logger.log(self.name, "Communications systems initializing...")
                    self.bus.send(self.name, "MissionLead", "TASK_COMPLETE: boot_comms")
                    continue

                # Default maintenance behavior
                self.logger.log(self.name, "Performing system maintenance...")
                self.state["maintenance_tasks"] += 1
                self.state["last_task_time"] = datetime.now().isoformat()

                report = f"Maintenance task #{self.state['maintenance_tasks']} complete at {self.state['last_task_time']}"
                self.bus.send(self.name, "MissionLead", report)
                self.logger.log(self.name, f"Sent to MissionLead: {report}")

                # Mark the task complete
                self.bus.send(self.name, "MissionLead", f"TASK_COMPLETE: {content}")
                self.logger.log(self.name, f"Sent TASK_COMPLETE: {content}")

                # Specific action logging
                if content == "adjust_thrusters":
                    self.logger.log(self.name, "Adjusting RCS thruster alignment...")
                elif content == "calibrate_radiators":
                    self.logger.log(self.name, "Calibrating thermal radiators to optimal flow...")
                elif content == "dump_propellant":
                    self.logger.log(self.name, "Emergency propellant dump initiated!")

            time.sleep(1)
