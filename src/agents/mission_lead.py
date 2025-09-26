import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from utils.planner import check_conditions


class MissionLead:
    def __init__(self, logger, bus):
        self.name = "MissionLead"
        self.logger = logger
        self.bus = bus
        self.state: Dict[str, Any] = {
            "tasks": {},
            "agents": {},
        }
        self.abort_mission = "emergency_abort.json"
        self._abort_mode = False
        self._abort_requested = False

    def log(self, message: str) -> None:
        self.logger.log(self.name, message)

    def load_mission(self, filename: str) -> Dict[str, Any]:
        path = os.path.join("missions", filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:  # pragma: no cover - runtime safety
            self.log(f"ERROR loading mission file: {e}")
            return {"name": "invalid", "steps": []}

    def trigger_emergency_abort(self, reason: str) -> None:
        if self._abort_mode:
            self.log(f"Abort already in progress. Ignoring trigger: {reason}")
            return
        self._abort_requested = True
        self.log(f"Emergency abort triggered due to {reason}.")
        previous_mode = self._abort_mode
        self._abort_mode = True
        self.run(self.abort_mission)
        self._abort_mode = previous_mode

    def _record_task_agent(self, action: str, sender: str) -> Dict[str, Any]:
        task_state = self.state.setdefault("tasks", {}).setdefault(
            action, {"agents": [], "status": None, "last_reason": None}
        )
        if sender and sender not in task_state["agents"]:
            task_state["agents"].append(sender)
        return task_state

    def _process_message(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        sender = msg.get("from", "")
        content = msg.get("content", "")
        self.log(f"Received from {sender}: {content}")

        if isinstance(content, str) and content.startswith("TASK_COMPLETE:"):
            action = content.split(":", 1)[1].strip()
            task_state = self._record_task_agent(action, sender)
            task_state["status"] = "COMPLETE"
            return {"type": "complete", "action": action, "sender": sender}

        if isinstance(content, str) and content.startswith("FAILURE:"):
            remainder = content.split(":", 1)[1].strip()
            action_part, _, reason = remainder.partition("|")
            action = action_part.strip()
            reason = reason.strip()
            task_state = self._record_task_agent(action, sender)
            task_state["status"] = "FAILED"
            task_state["last_reason"] = reason
            self.log(f"Task {action} reported failure by {sender}: {reason}")
            return {
                "type": "failure",
                "action": action,
                "sender": sender,
                "reason": reason,
            }

        if isinstance(content, str) and content.startswith("SYSTEM_FAILURE:"):
            failure_type = content.split(":", 1)[1].strip()
            self.log(f"System failure detected: {failure_type}")
            self.trigger_emergency_abort(f"system failure: {failure_type}")
            return {
                "type": "system_failure",
                "detail": failure_type,
                "sender": sender,
            }

        if isinstance(content, str) and content.startswith("AGENT_HEALTH:"):
            status = content.split(":", 1)[1].strip()
            self.state.setdefault("agents", {})[sender] = status
            self.log(f"Agent {sender} health status updated: {status}")
            if status.upper() == "FAILED":
                self.trigger_emergency_abort(f"agent {sender} health failure")
            return {"type": "health", "status": status, "sender": sender}

        return None

    def _dispatch_step(
        self,
        action: str,
        recipients: List[str],
        metadata: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        if not recipients:
            return True, None

        for recipient in recipients:
            self.bus.send(self.name, recipient, metadata)

        pending = set(recipients)
        timeout = metadata.get("timeout")
        start_time = time.time()
        failure_reason: Optional[str] = None

        while pending and not self._abort_requested:
            if timeout and time.time() - start_time > timeout:
                failure_reason = f"Timeout after {timeout}s"
                self.log(f"Step {action} timed out: {failure_reason}.")
                break

            messages = self.bus.fetch(self.name)
            if not messages:
                time.sleep(0.2)
                continue

            for msg in messages:
                result = self._process_message(msg)
                if not result:
                    continue
                if result["type"] == "complete" and result["action"] == action:
                    pending.discard(result["sender"])
                elif result["type"] == "failure" and result["action"] == action:
                    pending.discard(result["sender"])
                    failure_reason = result.get("reason") or "Agent reported failure"
            if self._abort_requested:
                break

        if pending and failure_reason is None:
            failure_reason = "Pending recipients did not respond"

        success = not pending and failure_reason is None
        return success, failure_reason

    def run(self, mission_filename: str) -> None:
        mission = self.load_mission(mission_filename)
        if not mission.get("steps"):
            self.log("Mission contains no steps. Nothing to execute.")
            return

        is_abort_mission = mission_filename == self.abort_mission
        previous_abort_state = self._abort_mode
        if is_abort_mission:
            self._abort_mode = True
        self._abort_requested = False if is_abort_mission else self._abort_requested

        self.log(f"Starting mission: {mission.get('name', mission_filename)}")

        steps = mission.get("steps", [])
        tracked_actions = [
            step.get("action")
            for step in steps
            if step.get("action") and step.get("recipients")
        ]

        for step in steps:
            if self._abort_requested and not is_abort_mission:
                self.log("Abort requested. Halting current mission execution.")
                break

            action = step.get("action")
            if not action:
                continue

            recipients = [
                r for r in step.get("recipients", []) if r and r != self.name
            ]

            conditions = step.get("conditions")
            if conditions and not check_conditions(self.state, conditions):
                self.log(f"Skipping {action}: mission conditions unmet -> {conditions}.")
                continue

            metadata = {
                "action": action,
                "conditions": step.get("conditions"),
                "retries": step.get("retries", 1),
                "timeout": step.get("timeout"),
                "retry_delay": step.get("retry_delay", 0.5),
            }

            success, failure_reason = self._dispatch_step(action, recipients, metadata)
            task_state = self.state.setdefault("tasks", {}).setdefault(
                action, {"agents": [], "status": None, "last_reason": None}
            )
            if success:
                task_state["status"] = "COMPLETE"
                self.log(f"Step {action} completed successfully.")
            else:
                task_state["status"] = "FAILED"
                task_state["last_reason"] = failure_reason
                self.log(f"Step {action} marked as FAILURE: {failure_reason}.")

            if self._abort_requested and not is_abort_mission:
                break

        # Process any remaining messages to keep state consistent
        leftover_messages = self.bus.fetch(self.name)
        for msg in leftover_messages:
            self._process_message(msg)

        # Final summary
        completed = [
            action
            for action in tracked_actions
            if self.state.get("tasks", {}).get(action, {}).get("status") == "COMPLETE"
        ]
        total = len(tracked_actions)
        self.log(f"Completed {len(completed)}/{total} tracked steps.")
        if len(completed) >= total and total > 0:
            self.log("All tracked tasks successfully completed. Mission is complete.")
        elif total > 0:
            self.log("Mission ended with incomplete or failed tasks.")

        self._abort_mode = previous_abort_state
        if not is_abort_mission:
            self._abort_requested = False
