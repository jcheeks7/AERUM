import time

class MissionLead:
    def __init__(self, logger, bus):
        self.logger = logger
        self.bus = bus
        self.name = "MissionLead"

    def run(self):
        self.logger.log(self.name, "Starting mission: debris_removal")
        actions = ["boot_all_systems", "scan_environment", "calculate_maneuver", "execute_maneuver", "report_status"]
        for i, action in enumerate(actions):
            self.logger.log(self.name, f"Action: {action}")
            self.bus.send(self.name, "OrbitalEngineer", f"Notify: {action} complete")
            time.sleep(0.1)
