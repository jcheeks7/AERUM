import time
import json
import os

class MissionLead:
    def __init__(self, logger, bus):
        self.name = "MissionLead"
        self.logger = logger
        self.bus = bus

    def load_mission(self, filename):
        path = os.path.join("missions", filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.log(self.name, f"ERROR loading mission file: {e}")
            return {"name": "invalid", "steps": []}

    def run(self, mission_filename):
        mission = self.load_mission(mission_filename)
        self.logger.log(self.name, f"Starting mission: {mission['name']}")

        external_steps = []
        internal_actions = []
        for step in mission.get("steps", []):
            action = step.get("action")
            recipients = [r for r in step.get("recipients", []) if r != self.name]
            if recipients:
                external_steps.append((action, recipients))
            else:
                internal_actions.append(action)

        valid_actions = [action for action, _ in external_steps]
        abort_mission = "emergency_abort.json"

        for action, recipients in external_steps:
            # check for system failures before each step
            failure_msgs = self.bus.fetch(self.name)
            for msg in failure_msgs:
                content = msg.get("content", "")
                if content.startswith("SYSTEM_FAILURE:"):
                    failure_type = content.split(":", 1)[1].strip()
                    self.logger.log(self.name, f"System failure detected: {failure_type}")
                    self.logger.log(self.name, "Initiating abort sequence")
                    self.run(abort_mission)
                    return
            # execute normal mission step
            self.logger.log(self.name, f"Action: {action}")
            time.sleep(1)
            for recipient in recipients:
                self.bus.send(self.name, recipient, action)

        time.sleep(1.5)
        messages = self.bus.fetch(self.name)

        completed = set(internal_actions)
        for msg in messages:
            content = msg.get("content", "")
            sender = msg.get("from", "")
            self.logger.log(self.name, f"Received from {sender}: {content}")
            if content.startswith("TASK_COMPLETE:"):
                task = content.split("TASK_COMPLETE:", 1)[1].strip()
                if task in valid_actions:
                    completed.add(task)

        total = len(valid_actions)
        success_count = len([a for a in completed if a in valid_actions])
        self.logger.log(self.name, f"Completed {success_count}/{total} steps.")
        if success_count >= total:
            self.logger.log(self.name, "All tasks successfully completed. Mission is complete.")
        else:
            self.logger.log(self.name, "Mission ended with incomplete tasks.")
