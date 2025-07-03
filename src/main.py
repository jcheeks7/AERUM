import threading
from utils.logger import Logger
from utils.message_bus import MessageBus
from agents.mission_lead import MissionLead
from agents.orbital_engineer import OrbitalEngineer
from agents.mission_specialist import MissionSpecialist
from agents.spacecraft_technician import SpacecraftTechnician

logger = Logger()
bus = MessageBus()

mission_lead = MissionLead(logger, bus)
orbital_engineer = OrbitalEngineer(logger, bus)
mission_specialist = MissionSpecialist(logger, bus)
spacecraft_technician = SpacecraftTechnician(logger, bus)

# Run passive agents in background threads
threading.Thread(target=orbital_engineer.run, daemon=True).start()
threading.Thread(target=mission_specialist.run, daemon=True).start()
threading.Thread(target=spacecraft_technician.run, daemon=True).start()

# MissionLead runs in the main thread
mission_lead.run()
