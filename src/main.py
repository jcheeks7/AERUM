import os
import threading
import time
import curses
from collections import deque
from datetime import datetime
from utils.logger import Logger
from utils.message_bus import MessageBus
from agents.mission_lead import MissionLead
from agents.orbital_engineer import OrbitalEngineer
from agents.mission_specialist import MissionSpecialist
from agents.spacecraft_technician import SpacecraftTechnician

# UI state buffers
global log_buffer, agent_status
log_buffer = deque(maxlen=100)
agent_status = {}

# Wrap logger to update UI buffers
def wrap_logger_for_ui(logger):
    orig_log = logger.log
    def ui_log(agent, message):
        orig_log(agent, message)
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_buffer.append(f"{timestamp}  [{agent}] {message}")
        agent_status[agent] = message
    logger.log = ui_log

# Dashboard UI using curses
def dashboard_loop(stdscr, mission_file, mission_lead, bus):
    curses.curs_set(0)
    stdscr.nodelay(True)
    height, width = stdscr.getmaxyx()

    # Start mission execution in background thread
    def start_mission():
        mission_lead.run(mission_file)
    threading.Thread(target=start_mission, daemon=True).start()

    while True:
        stdscr.erase()
        # Header
        stdscr.addstr(0, 2, f"📡 AERUM MISSION CONTROL  -  Mission: {mission_file}")
        stdscr.addstr(1, 2, "Press 'q' to quit")
        # Agent status panel
        stdscr.addstr(3, 2, "Agent Status:")
        row = 4
        for agent, status in agent_status.items():
            stdscr.addstr(row, 4, f"{agent}: {status}")
            row += 1
        # Log panel
        stdscr.addstr(3, width // 2, "Log:")
        log_start = max(0, len(log_buffer) - (height - 5))
        for idx, entry in enumerate(list(log_buffer)[log_start:]):
            stdscr.addstr(4 + idx, width // 2, entry[: width // 2 - 1])
        stdscr.refresh()

        # Input handling
        try:
            ch = stdscr.getkey()
            if ch.lower() == 'q':
                break
        except curses.error:
            pass
        time.sleep(0.2)

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

# Main entrypoint
def main():
    logger = Logger()
    wrap_logger_for_ui(logger)
    bus = MessageBus()

    mission_file = select_mission()

    mission_lead = MissionLead(logger, bus)
    orbital_engineer = OrbitalEngineer(logger, bus)
    mission_specialist = MissionSpecialist(logger, bus)
    spacecraft_technician = SpacecraftTechnician(logger, bus)

    # Launch agents in background threads
    threading.Thread(target=orbital_engineer.run, daemon=True).start()
    threading.Thread(target=mission_specialist.run, daemon=True).start()
    threading.Thread(target=spacecraft_technician.run, daemon=True).start()

    # Start the curses dashboard (blocks until 'q')
    curses.wrapper(dashboard_loop, mission_file, mission_lead, bus)

if __name__ == "__main__":
    main()
