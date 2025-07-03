import time
import json
import os

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

    def load_mission(self, filename):
        """Load mission steps from a JSON file."""
        path = os.path.join("missions", filename)
        try:
            with open(path, "r") as f:
                mission = json.load(f)
            return mission
        except Exception as e:
            self.logger.log(self.name, f"ERROR loading mission file: {e}")
            return {"name": "invalid", "steps": []}

    def run(self, mission_filename):
        mission = self.load_mission(mission_filename)
        self.logger.log(self.name, f"Starting mission: {mission['name']}")

        # Execute mission steps
        for step in mission["steps"]:
            action = step["action"]
            recipients = step["recipients"]

            self.logger.log(self.name, f"Action: {action}")
            time.sleep(1)

            for recipient in recipients:
                message = f"Notify: {action} complete"
                self.bus.send(self.name, recipient, message)

        # Collect final reports from agents
        time.sleep(1.5)
        messages = self.bus.fetch(self.name)
        for msg in messages:
            self.logger.log(self.name, f"Received from {msg['from']}: {msg['content']}")
            self.state["responses_received"] += 1

        # Final mission summary
        if self.state["responses_received"] >= self.state["expected_responses"]:
            self.logger.log(self.name, "All agents have reported back. Mission is complete.")
            self.state["mission_complete"] = True
