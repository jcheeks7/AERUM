class SpacecraftTechnician:
    def __init__(self, logger, bus):
        self.logger = logger
        self.bus = bus
        self.name = "SpacecraftTechnician"

    def run(self):
        for _ in range(5):
            messages = self.bus.fetch(self.name)
            for msg in messages:
                self.logger.log(self.name, f"Received from {msg['from']}: {msg['content']}")
                self.logger.log(self.name, f"Thrust systems nominal")
            time.sleep(0.1)# Spacecraft Technician agent logic placeholder
