import time

class MissionLead:
    def __init__(self, logger, bus):
        self.name = "MissionLead"
        self.logger = logger
        self.bus = bus
        self.state = {
            "responses_received": 0,
            "expected_responses": 3,
            "mission_complete": False
        }

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
            time.sleep(1)
            for recipient in recipients:
                self.bus.send(self.name, recipient, f"Notify: {action} complete")

        # Wait and process incoming agent reports
        time.sleep(1.5)
        messages = self.bus.fetch(self.name)
        for msg in messages:
            self.logger.log(self.name, f"Received from {msg['from']}: {msg['content']}")
            self.state["responses_received"] += 1

        if self.state["responses_received"] >= self.state["expected_responses"]:
            self.logger.log(self.name, "All agents have reported back. Mission is complete.")
            self.state["mission_complete"] = True
