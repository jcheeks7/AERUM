from agents.mission_lead import MissionLead
from agents.orbital_engineer import OrbitalEngineer
from agents.mission_specialist import MissionSpecialist
from utils.logger import Logger
import time

# Initialize logger
logger = Logger("mission_log.txt")

# Initialize agents
mission_lead = MissionLead(logger)
orbital_engineer = OrbitalEngineer(logger)
mission_specialist = MissionSpecialist(logger)

# Message bus for communication
message_bus = []

# Run the mission
mission_lead.run_mission(message_bus)

# Distribute messages to other agents
for message in message_bus:
    orbital_engineer.receive_message(message)
    mission_specialist.receive_message(message)
