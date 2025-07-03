from agents.mission_lead import MissionLead
from agents.orbital_engineer import OrbitalEngineer
from agents.mission_specialist import MissionSpecialist
from utils.logger import Logger
import time

# Initialize logger
logger = Logger()

# Message bus for communication
message_bus = []

# Initialize agents with both logger and bus
mission_lead = MissionLead(logger, message_bus)
orbital_engineer = OrbitalEngineer(logger)
mission_specialist = MissionSpecialist(logger)

# Run the mission
mission_lead.run_mission()

# Distribute messages to other agents
for message in message_bus:
    orbital_engineer.receive_message(message)
    mission_specialist.receive_message(message)

