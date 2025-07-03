import os
import threading
import time
from utils.logger import Logger
from utils.message_bus import MessageBus
from agents.mission_lead import MissionLead
from agents.orbital_engineer import OrbitalEngineer
from agents.mission_specialist import MissionSpecialist
from agents.spacecraft_technician import SpacecraftTechnician

# CLI mission selector
def select_mission():
    mission_dir = os.path.join("missions")
    files = [f for f in os.listdir(mission_dir) if f.endswith(".json")]

    print("📡 AERUM MISSION CONTROL")
    print("Select a mission:\n")

    for i, file in enumerate(files, 1):
        print(f"[{i}] {file}")

    while True:
        try:
            choice = int(input("\n>> "))
            if 1 <= choice <= len(files):
                return files[choice - 1]
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a number.")

def main():
    logger = Logger()
    bus = MessageBus()

    mission_file = select_mission()

    mission_lead = MissionLead(logger, bus)
    orbital_engineer = OrbitalEngineer(logger, bus)
    mission_specialist = MissionSpecialist(logger, bus)
    spacecraft_technician = SpacecraftTechnician(logger, bus)

    # Background threads
    threading.Thread(target=orbital_engineer.run, daemon=True).start()
    threading.Thread(target=mission_specialist.run, daemon=True).start()
    threading.Thread(target=spacecraft_technician.run, daemon=True).start()

    # Run selected mission
    mission_lead.run(mission_file)

    time.sleep(3)

if __name__ == "__main__":
    main()
