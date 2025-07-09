import time
import json
import os

class MissionLead:
    def __init__(self, logger, bus):
        self.name = "MissionLead"
        self.logger = logger
        self.bus = bus

    def load_mission(self, filename):
        """Load mission steps from a JSON file."""
        path = os.path.join("missions", filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                mission = json.load(f)
            return mission
        except Exception as e:
            self.logger.log(self.name, f"ERROR loading mission file: {e}")
            return {"name": "invalid", "steps": []}

    def run(self, mission_filename):
        mission = self.load_mission(mission_filename)
        self.logger.log(self.name, f"Starting mission: {mission['name']}")

        external_steps = []
        internal_completed = []
        for step in mission.get("steps", []):
            action = step.get("action")
            recipients = [r for r in step.get("recipients", []) if r != self.name]
            if recipients:
                external_steps.append((action, recipients))
            else:
                internal_completed.append(action)

        valid_actions = [action for action, _ in external_steps]

        for action, recipients in external_steps:
            self.logger.log(self.name, f"Action: {action}")
            time.sleep(1)
            for recipient in recipients:
                self.bus.send(self.name, recipient, action)

        time.sleep(1.5)
        messages = self.bus.fetch(self.name)

        completed = set(internal_completed)
        for msg in messages:
            content = msg.get("content", "")
            sender = msg.get("from", "")
            self.logger.log(self.name, f"Received from {sender}: {content}")
            if content.startswith("TASK_COMPLETE:" ):
                action = content.split("TASK_COMPLETE:", 1)[1].strip()
                if action in valid_actions:
                    completed.add(action)

        total = len(valid_actions)
        completed_count = len([a for a in completed if a in valid_actions])
        self.logger.log(self.name, f"Completed {completed_count}/{total} steps.")
        if completed_count >= total:
            self.logger.log(self.name, "All tasks successfully completed. Mission is complete.")
        else:
            self.logger.log(self.name, "⚠Mission ended with incomplete tasks.")
