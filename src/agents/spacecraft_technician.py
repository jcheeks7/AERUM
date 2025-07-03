import time

class SpacecraftTechnician:
    def __init__(self, logger, bus):
        self.name = "SpacecraftTechnician"
        self.logger = logger
        self.bus = bus

    def run(self):
        while True:
            messages = self.bus.fetch(self.name)
            for msg in messages:
                self.logger.log(self.name, f"Received from {msg['from']}: {msg['content']}")
                self.logger.log(self.name, "Performing system maintenance...")
            time.sleep(1)
