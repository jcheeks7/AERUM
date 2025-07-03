from logger import Logger
from message_bus import MessageBus
from agents.mission_lead import MissionLead
from agents.orbital_engineer import OrbitalEngineer
from agents.spacecraft_technician import SpacecraftTechnician

logger = Logger()
bus = MessageBus()

agents = [
    MissionLead(logger, bus),
    OrbitalEngineer(logger, bus),
    SpacecraftTechnician(logger, bus)
]

for agent in agents:
    agent.run()

logger.export()
