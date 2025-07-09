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

        for step in mission["steps"]:
            action = step["action"]
            recipients = step["recipients"]

            self.logger.log(self.name, f"Action: {action}")
            time.sleep(1)

            if not recipients:
            self.state["completed_actions"].append(action)
            continue

            for recipient in recipients:
                message = f"Notify: {action} complete"
                self.bus.send(self.name, recipient, message)


        time.sleep(1.5)
        messages = self.bus.fetch(self.name)
        
        completed_steps = 0
        total_steps = len(mission["steps"])

        for msg in messages:
            self.logger.log(self.name, f"Received from {msg['from']}: {msg['content']}")
            if msg["content"].startswith("TASK_COMPLETE:"):
                completed_steps += 1
            self.state["responses_received"] += 1


        self.logger.log(self.name, f"Completed {completed_steps}/{total_steps} steps.")
        if completed_steps >= total_steps:
            self.logger.log(self.name, "All tasks successfully completed. Mission is complete.")
            self.state["mission_complete"] = True
        else:
            self.logger.log(self.name, "Mission ended with incomplete tasks.") 
