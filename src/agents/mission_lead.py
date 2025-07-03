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
        path = os.path.join("..", "missions", filename)
        with open(path, "r") as f:
            mission = json.load(f)
        return mission

    def run(self, mission_filename):
        mission = self.load_mission(mission_filename)
        self.logger.log(self.name, f"Starting mission: {mission['name']}")

        for step in mission["steps"]:
            action = step["action"]
            recipients = step["recipients"]

            self.logger.log(self.name, f"Action: {action}")
            time.sleep(1)
            for recipient in recipients:
                self.bus.send(self.name, recipient, f"Notify: {action} complete")

        # Wait for responses
        time.sleep(1.5)
        messages = self.bus.fetch(self.name)
        for msg in messages:
            self.logger.log(self.name, f"Received from {msg['from']}: {msg['content']}")
            self.state["responses_received"] += 1

        if self.state["responses_received"] >= self.state["expected_responses"]:
            self.logger.log(self.name, "All agents have reported back. Mission is complete.")
            self.state["mission_complete"] = True
