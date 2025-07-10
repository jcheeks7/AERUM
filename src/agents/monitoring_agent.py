import time
from datetime import datetime

class MonitoringAgent:
    def __init__(self, logger, bus, interval=1):
        self.name = "SystemMonitor"
        self.logger = logger
        self.bus = bus
        self.interval = interval
        self.state = {
            "power_ok": True,
            "comms_ok": True
        }
        # Track which boot steps are pending acknowledgment
        self.boot_pending = {"boot_power", "boot_comms"}

    def check_power(self):
        return self.state["power_ok"]

    def check_comms(self):
        return self.state["comms_ok"]

    def run(self):
        while True:
            # Handle incoming messages
            messages = self.bus.fetch(self.name)
            for msg in messages:
                content = msg["content"]
                sender = msg["from"]
                self.logger.log(self.name, f"Received from {sender}: {content}")

                # Boot power handling
                if content == "boot_power":
                    if self.state["power_ok"]:
                        self.logger.log(self.name, "Verifying power system startup...")
                        self.bus.send(self.name, "MissionLead", "TASK_COMPLETE: boot_power")
                        self.boot_pending.discard("boot_power")
                    else:
                        self.logger.log(self.name, "Power system failure detected during boot")
                        self.bus.send(self.name, "MissionLead", "SYSTEM_FAILURE: power")
                    continue

                # Boot comms handling
                if content == "boot_comms":
                    if self.state["comms_ok"]:
                        self.logger.log(self.name, "Verifying communications system startup...")
                        self.bus.send(self.name, "MissionLead", "TASK_COMPLETE: boot_comms")
                        self.boot_pending.discard("boot_comms")
                    else:
                        self.logger.log(self.name, "Communications failure detected during boot")
                        self.bus.send(self.name, "MissionLead", "SYSTEM_FAILURE: comms")
                    continue

                # Repair handlers
                if content == "fix_power":
                    self.logger.log(self.name, "Power system repaired, resetting status...")
                    self.state["power_ok"] = True
                    self.bus.send(self.name, "MissionLead", "TASK_COMPLETE: fix_power")
                    continue

                if content == "fix_comms":
                    self.logger.log(self.name, "Communications system repaired, resetting status...")
                    self.state["comms_ok"] = True
                    self.bus.send(self.name, "MissionLead", "TASK_COMPLETE: fix_comms")
                    continue

            # After boot sequence completes, regular health monitoring
            if not self.boot_pending:
                if not self.check_power():
                    self.logger.log(self.name, "Power system failure detected")
                    self.bus.send(self.name, "MissionLead", "SYSTEM_FAILURE: power")
                if not self.check_comms():
                    self.logger.log(self.name, "Communications failure detected")
                    self.bus.send(self.name, "MissionLead", "SYSTEM_FAILURE: comms")

            time.sleep(self.interval)
