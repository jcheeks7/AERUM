import time

class MissionSpecialist:
    def __init__(self, logger, bus):
        self.name = "MissionSpecialist"
        self.logger = logger
        self.bus = bus

    def run(self):
        while True:
            messages = self.bus.fetch(self.name)
            for msg in messages:
                self.logger.log(self.name, f"Received from {msg['from']}: {msg['content']}")
                self.logger.log(self.name, "Analyzing mission data...")
            time.sleep(1)
