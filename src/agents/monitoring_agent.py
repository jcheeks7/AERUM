import time

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
        # Placeholder for actual power check logic
        return self.state["power_ok"]

    def check_comms(self):
        # Placeholder for actual communications check logic
        return self.state["comms_ok"]

  # Need to add more checks (pressure, fuel, orbital trajectory, valve states, etc...)

    def run(self):
        while True:
            if not self.check_power():
                self.logger.log(self.name, "Power system failure detected")
                self.bus.send(self.name, "MissionLead", "SYSTEM_FAILURE: power")
            if not self.check_comms():
                self.logger.log(self.name, "Communications failure detected")
                self.bus.send(self.name, "MissionLead", "SYSTEM_FAILURE: comms")
            time.sleep(self.interval)
