import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

for path in (PROJECT_ROOT, SRC_ROOT):
    str_path = str(path)
    if str_path not in sys.path:
        sys.path.insert(0, str_path)

from main import run_boot_sequence
from utils.message_bus import MessageBus


class DummyLogger:
    def __init__(self):
        self.entries = []

    def log(self, agent, message):
        self.entries.append((agent, message))


class BootTestBus(MessageBus):
    def __init__(self):
        super().__init__()
        self.failure_injected = False

    def send(self, sender, recipient, content):
        super().send(sender, recipient, content)
        if sender == "MissionLead" and isinstance(content, str):
            if content.startswith("boot_"):
                if recipient == "SpacecraftTechnician":
                    if not self.failure_injected:
                        self.failure_injected = True
                        super().send(
                            "SpacecraftTechnician",
                            "MissionLead",
                            f"FAILURE: {content} | actuator jam",
                        )
                    else:
                        super().send(
                            "SpacecraftTechnician",
                            "MissionLead",
                            f"TASK_COMPLETE: {content}",
                        )
                elif recipient == "SystemMonitor":
                    super().send(
                        "SystemMonitor",
                        "MissionLead",
                        f"TASK_COMPLETE: {content}",
                    )
            elif content.startswith("fix_"):
                super().send(recipient, "MissionLead", f"TASK_COMPLETE: {content}")


def test_boot_sequence_retries_after_failure():
    logger = DummyLogger()
    bus = BootTestBus()

    result = run_boot_sequence(logger, bus, timeout=1.5)

    assert result is True

    failure_logs = [msg for agent, msg in logger.entries if "Failure reported" in msg]
    assert failure_logs, "Boot sequence should log failure details"

    retry_logs = [msg for agent, msg in logger.entries if "Retrying boot_power" in msg]
    assert retry_logs, "Boot sequence should retry the failed boot command"
