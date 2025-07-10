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

# Buffer for UI logs
log_buffer = deque(maxlen=200)
agent_status = {}

# Wrap logger to capture all agent messages in the UI log
def wrap_logger_for_ui(logger):
    orig_log = logger.log
    def ui_log(agent, message):
        orig_log(agent, message)
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        entry = f"[{timestamp}] [{agent}] {message}"
        log_buffer.append(entry)
        agent_status[agent] = message
    logger.log = ui_log

# Pre-mission boot sequence (unchanged)
def run_boot_sequence(logger, bus, timeout=5):
    """Sequentially boot subsystems with auto-repair and failure handling."""
    subsystems = ["power", "comms"]
    required_agents = ["SpacecraftTechnician", "SystemMonitor"]

    for sys in subsystems:
        action = f"boot_{sys}"
        while bus.fetch("MissionLead"): pass
        logger.log("MissionLead", f"Action: {action}")
        for agent in required_agents:
            bus.send("MissionLead", agent, action)
        start = time.time()
        acked = set()
        while time.time() - start < timeout and acked != set(required_agents):
            msgs = bus.fetch("MissionLead")
            for msg in msgs:
                sender = msg.get("from")
                content = msg.get("content", "")
                if content == f"TASK_COMPLETE: {action}":
                    acked.add(sender)
                    logger.log("MissionLead", f"Acknowledged {action} by {sender}")
                elif content.startswith("SYSTEM_FAILURE:"):
                    failure = content.split(":", 1)[1].strip()
                    if failure == sys:
                        logger.log("MissionLead", f"Boot failure detected: {failure}")
                        fix_cmd = f"fix_{failure}"
                        logger.log("MissionLead", f"Delegating fix: {fix_cmd}")
                        for a in required_agents:
                            bus.send("MissionLead", a, fix_cmd)
            time.sleep(0.1)
        if acked != set(required_agents):
            missing = set(required_agents) - acked
            logger.log("MissionLead", f"Boot incomplete. Missing acknowledgements from: {', '.join(missing)}")
            return False
    logger.log("MissionLead", "All systems nominal.")
    return True

# Dashboard UI: Agent Status, Task Status, Logs
def dashboard_loop(stdscr, mission_file, mission_lead, bus):
    curses.curs_set(0)
    stdscr.nodelay(True)
    threading.Thread(target=lambda: mission_lead.run(mission_file), daemon=True).start()

    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()

        # Header
        try:
            stdscr.addstr(0, 2, f"📡 AERUM MISSION CONTROL - Mission: {mission_file}")
            stdscr.addstr(1, 2, "Press 'q' to quit")
        except curses.error:
            pass

        # Agent Status Panel
        row = 3
        try:
            stdscr.addstr(row, 2, "Agent Status:")
        except curses.error:
            pass
        row += 1
        # truncate status to prevent wrapping
        max_col = width // 2 - 4
        for agent, status in agent_status.items():
            if row >= height - 1:
                break
            try:
                stdscr.addstr(row, 4, f"{agent}: {status}"[:max_col])
            except curses.error:
                pass
            row += 1

        # Task Status Panel (moved above logs)
        steps = mission_lead.load_mission(mission_file).get('steps', [])
        completed = {e.split("TASK_COMPLETE:",1)[1].strip() for e in log_buffer if "TASK_COMPLETE:" in e}
        task_col = (width // 2) + 2
        try:
            stdscr.addstr(3, task_col, "Task Status:")
        except curses.error:
            pass
        for idx, step in enumerate(steps, start=1):
            if 3 + idx >= height - 1:
                break
            ch = "✔" if step['action'] in completed else "✖"
            try:
                stdscr.addstr(3 + idx, task_col, f"{ch} {step['action']}"[:width-task_col-2])
            except curses.error:
                pass

        # Logs Panel (recent 15 entries)
        max_logs = 15
        recent_logs = list(log_buffer)[-max_logs:]
        log_row_start = len(steps) + 10
        col_mid = 2
        try:
            stdscr.addstr(log_row_start - 1, col_mid, "Logs:")
        except curses.error:
            pass
        log_row = log_row_start
        for entry in recent_logs:
            if log_row >= height - 1:
                break
            try:
                stdscr.addstr(log_row, col_mid, entry[:width-4])
            except curses.error:
                pass
            log_row += 1

        stdscr.refresh()
        try:
            if stdscr.getch() == ord('q'):
                break
        except curses.error:
            pass
        time.sleep(0.2)

# Mission selection via console
def select_mission():
    files = [f for f in os.listdir('missions') if f.endswith('.json')]
    print("📡 AERUM MISSION CONTROL")
    print("Select a mission:\n")
    for i, f in enumerate(files, 1):
        print(f"[{i}] {f}")
    while True:
        try:
            c = int(input("\n>> "))
            if 1 <= c <= len(files):
                return files[c-1]
        except:
            pass
        print("Invalid selection.")

if __name__ == "__main__":
    logger = Logger()
    wrap_logger_for_ui(logger)
    bus = MessageBus()

    tech = SpacecraftTechnician(logger, bus)
    mon = MonitoringAgent(logger, bus)
    threading.Thread(target=tech.run, daemon=True).start()
    threading.Thread(target=mon.run, daemon=True).start()

    if not run_boot_sequence(logger, bus):
        exit(1)

    mission = select_mission()
    engineer = OrbitalEngineer(logger, bus)
    specialist = MissionSpecialist(logger, bus)
    threading.Thread(target=engineer.run, daemon=True).start()
    threading.Thread(target=specialist.run, daemon=True).start()

    lead = MissionLead(logger, bus)
    curses.wrapper(dashboard_loop, mission, lead, bus)
