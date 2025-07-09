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

    def check_power(self):
        return self.state["power_ok"]

    def check_comms(self):
        return self.state["comms_ok"]

    def run(self):
        while True:
            messages = self.bus.fetch(self.name)
            for msg in messages:
                content = msg["content"]
                sender = msg["from"]
                self.logger.log(self.name, f"Received from {sender}: {content}")
                if content == "boot_power":
                    self.logger.log(self.name, "Verifying power system startup...")
                    self.bus.send(self.name, "MissionLead", "TASK_COMPLETE: boot_power")
                elif content == "boot_comms":
                    self.logger.log(self.name, "Verifying communications system startup...")
                    self.bus.send(self.name, "MissionLead", "TASK_COMPLETE: boot_comms")

            if not self.check_power():
                self.logger.log(self.name, "Power system failure detected")
                self.bus.send(self.name, "MissionLead", "SYSTEM_FAILURE: power")
            if not self.check_comms():
                self.logger.log(self.name, "Communications failure detected")
                self.bus.send(self.name, "MissionLead", "SYSTEM_FAILURE: comms")

            time.sleep(self.interval)
