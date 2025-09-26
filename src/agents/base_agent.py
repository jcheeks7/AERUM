import random
from typing import Any, Callable, Dict, Optional

from utils.planner import check_conditions, retry_action, timeout_wrapper


class BaseAgent:
    HEALTH_OK = "OK"
    HEALTH_DEGRADED = "DEGRADED"
    HEALTH_FAILED = "FAILED"

    def __init__(self, name: str, logger, bus):
        self.name = name
        self.logger = logger
        self.bus = bus
        self.health = self.HEALTH_OK
        self.failure_probability = 0.05
        self.state: Dict[str, Any] = {}

    def log(self, message: str) -> None:
        self.logger.log(self.name, message)

    def send(self, recipient: str, content: Any) -> None:
        self.bus.send(self.name, recipient, content)

    def maybe_fail(self) -> bool:
        if self.health == self.HEALTH_FAILED:
            self.log("Action prevented: health status is FAILED.")
            return True

        probability = self.failure_probability
        if self.health == self.HEALTH_DEGRADED:
            probability = min(1.0, probability * 2)

        outcome = random.random() < probability
        if outcome:
            self.log(f"Probabilistic failure triggered (p={probability:.2f}).")
        return outcome

    def degrade_health(self) -> None:
        previous = self.health
        if self.health == self.HEALTH_OK:
            self.health = self.HEALTH_DEGRADED
        elif self.health == self.HEALTH_DEGRADED:
            self.health = self.HEALTH_FAILED

        if self.health != previous:
            self.log(f"Health changed from {previous} to {self.health}.")
            if self.health == self.HEALTH_FAILED:
                self.send("MissionLead", "AGENT_HEALTH: FAILED")
        else:
            self.log(f"Health remains {self.health} after failure event.")

    def repair_health(self) -> None:
        if self.health != self.HEALTH_OK:
            previous = self.health
            self.health = self.HEALTH_OK
            self.log(f"Health repaired from {previous} to {self.health}.")
        else:
            self.log("Repair command received but health already OK.")

    def report_failure(self, action_name: str, reason: str) -> None:
        message = f"FAILURE: {action_name} | {reason}"
        self.log(f"Reporting failure: {message}")
        self.send("MissionLead", message)

    def execute_with_resilience(
        self,
        action_name: str,
        action_fn: Callable[[], Any],
        *,
        conditions: Optional[Dict[str, Any]] = None,
        retries: Optional[int] = 1,
        timeout: Optional[float] = None,
        retry_delay: float = 0.5,
        state: Optional[Dict[str, Any]] = None,
    ) -> Any:
        current_state = state if state is not None else self.state
        state_context: Dict[str, Any] = {}
        if isinstance(current_state, dict):
            state_context.update(current_state)
            state_context.setdefault("state", current_state)
        else:
            state_context["state"] = current_state

        if conditions and not check_conditions(state_context, conditions):
            self.log(f"Skipping {action_name}: unmet conditions {conditions}.")
            return None

        attempts = max(1, retries if retries is not None else 1)

        def attempt_fn(attempt_number: int):
            if self.maybe_fail():
                raise RuntimeError("Probabilistic failure triggered")

            def run_action():
                return action_fn()

            try:
                if timeout:
                    return timeout_wrapper(run_action, timeout)
                return run_action()
            except Exception as exc:
                if attempt_number < attempts:
                    self.log(
                        f"Attempt {attempt_number} for {action_name} failed: {exc}. "
                        f"Retrying in {retry_delay}s."
                    )
                raise

        try:
            result = retry_action(attempt_fn, attempts, retry_delay)
            if attempts > 1:
                self.log(f"Action {action_name} completed after {attempts} attempts or fewer.")
            return result
        except TimeoutError as exc:
            self.log(f"Action {action_name} timed out: {exc}.")
            self.report_failure(action_name, str(exc))
            self.degrade_health()
        except Exception as exc:
            self.log(f"Action {action_name} failed after {attempts} attempts: {exc}.")
            self.report_failure(action_name, str(exc))
            self.degrade_health()
        return None
