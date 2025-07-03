# src/agents/mission_lead.py
import time

class MissionLead:
    def __init__(self, logger, bus):
        self.name = "MissionLead"
        self.logger = logger
        self.bus = bus

    def run(self):
        self.logger.log(self.name, "Starting mission: debris_removal")
        steps = [
            ("boot_all_systems", ["OrbitalEngineer", "MissionSpecialist", "SpacecraftTechnician"]),
            ("scan_environment", ["MissionSpecialist"]),
            ("calculate_maneuver", ["OrbitalEngineer"]),
            ("execute_burn", ["SpacecraftTechnician"])
        ]

        for action, recipients in steps:
            self.logger.log(self.name, f"Action: {action}")
            time.sleep(1)  # Simulate time taken
            for recipient in recipients:
                self.bus.send(self.name, recipient, f"Notify: {action} complete")
