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
from agents.monitoring_agent import MonitoringAgent

log_buffer = deque(maxlen=100)
agent_status = {}

def wrap_logger_for_ui(logger):
    orig_log = logger.log
    def ui_log(agent, message):
        orig_log(agent, message)
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_buffer.append(f"{timestamp}  [{agent}] {message}")
        agent_status[agent] = message
    logger.log = ui_log

# Pre-mission boot sequence

def run_boot_sequence(logger, bus, timeout=5):
    boot_actions = ["boot_power", "boot_comms"]
    acked = set()
    failure_detected = False
    start = time.time()

    for action in boot_actions:
        logger.log("MissionLead", f"Action: {action}")
        for agent in ["OrbitalEngineer", "MissionSpecialist", "SpacecraftTechnician", "SystemMonitor"]:
            bus.send("MissionLead", agent, action)

    while time.time() - start < timeout and len(acked) < len(boot_actions):
        msgs = bus.fetch("MissionLead")
        for msg in msgs:
            content = msg.get("content", "")
            if content.startswith("TASK_COMPLETE:"):
                act = content.split("TASK_COMPLETE:", 1)[1].strip()
                if act in boot_actions:
                    acked.add(act)
            elif content.startswith("SYSTEM_FAILURE:"):
                failure = content.split(":", 1)[1].strip()
                failure_detected = True
                logger.log("MissionLead", f"Boot failure detected: {failure}")
                fix_action = f"fix_{failure}"
                logger.log("MissionLead", f"Delegating fix: {fix_action} to SpacecraftTechnician")
                bus.send("MissionLead", "SpacecraftTechnician", fix_action)
        time.sleep(0.1)

    if failure_detected:
        logger.log("MissionLead", "Boot sequence incomplete. Please troubleshoot.")
        return False
    if len(acked) == len(boot_actions):
        logger.log("MissionLead", "All systems nominal.")
        return True
    missing = set(boot_actions) - acked
    logger.log("MissionLead", f"Boot incomplete. Missing acknowledgements: {', '.join(missing)}")
    return False

# Curses-based dashboard

def dashboard_loop(stdscr, mission_file, mission_lead, bus):
    curses.curs_set(0)
    stdscr.nodelay(True)
    height, width = stdscr.getmaxyx()

    mission_data = mission_lead.load_mission(mission_file)
    actions = [step.get('action') for step in mission_data.get('steps', [])]
    tasks_completed = set()

    def start_mission():
        mission_lead.run(mission_file)
    threading.Thread(target=start_mission, daemon=True).start()

    while True:
        stdscr.erase()
        stdscr.addstr(0, 2, f"📡 AERUM MISSION CONTROL  -  Mission: {mission_file}")
        stdscr.addstr(1, 2, "Press 'q' to quit")
        stdscr.addstr(3, 2, "Agent Status:")
        row = 4
        for agent, status in agent_status.items():
            stdscr.addstr(row, 4, f"{agent}: {status}")
            row += 1

        stdscr.addstr(row + 1, 2, "Task Status:")
        row += 2
        for entry in list(log_buffer):
            if "TASK_COMPLETE:" in entry:
                action = entry.split("TASK_COMPLETE:", 1)[1].strip()
                tasks_completed.add(action)
        for action in actions:
            status_char = "✔" if action in tasks_completed else "✖"
            stdscr.addstr(row, 4, f"{status_char} {action}")
            row += 1

        stdscr.addstr(3, width // 2, "Log:")
        log_start = max(0, len(log_buffer) - (height - row - 2))
        for idx, entry in enumerate(list(log_buffer)[log_start:]):
            stdscr.addstr(row + idx, width // 2, entry[: width // 2 - 1])

        stdscr.refresh()
        try:
            ch = stdscr.getkey()
            if ch.lower() == 'q':
                break
        except curses.error:
            pass
        time.sleep(0.2)

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

# Entry point

def main():
    logger = Logger()
    wrap_logger_for_ui(logger)
    bus = MessageBus()

    if not run_boot_sequence(logger, bus):
        return

    mission_file = select_mission()

    mission_lead = MissionLead(logger, bus)
    orbital_engineer = OrbitalEngineer(logger, bus)
    mission_specialist = MissionSpecialist(logger, bus)
    spacecraft_technician = SpacecraftTechnician(logger, bus)
    monitoring_agent = MonitoringAgent(logger, bus)

    threading.Thread(target=orbital_engineer.run, daemon=True).start()
    threading.Thread(target=mission_specialist.run, daemon=True).start()
    threading.Thread(target=spacecraft_technician.run, daemon=True).start()
    threading.Thread(target=monitoring_agent.run, daemon=True).start()

    curses.wrapper(dashboard_loop, mission_file, mission_lead, bus)

if __name__ == "__main__":
    main()
