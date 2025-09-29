import os
import threading
import time
from utils.logger import Logger
from utils.message_bus import MessageBus
from agents.mission_lead import MissionLead
from agents.orbital_engineer import OrbitalEngineer
from agents.mission_specialist import MissionSpecialist
from agents.spacecraft_technician import SpacecraftTechnician
from agents.monitoring_agent import MonitoringAgent
from interface.dashboard import launch_dashboard
from interface.event_store import event_store


def wrap_logger_for_ui(logger):
    """Proxy logger to capture log lines into the web dashboard event store."""

    original_log = logger.log

    def ui_log(agent, message):
        original_log(agent, message)
        event_store.record_event(agent, message)

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
                if isinstance(content, str) and content == f"TASK_COMPLETE: {action}":
                    acked.add(sender)
                    logger.log("MissionLead", f"Acknowledged {action} by {sender}")
                elif isinstance(content, str) and content.startswith("FAILURE:"):
                    payload = content.split("FAILURE:", 1)[1].strip()
                    failure_action = payload
                    failure_reason = "unknown"
                    if "|" in payload:
                        parts = payload.split("|", 1)
                        failure_action = parts[0].strip()
                        failure_reason = parts[1].strip()
                    if failure_action == action:
                        agent_name = sender or "Unknown"
                        logger.log(
                            "MissionLead",
                            f"Failure reported by {agent_name} for {action}: {failure_reason}",
                        )
                        if sender in acked:
                            acked.remove(sender)
                        if sender:
                            logger.log("MissionLead", f"Retrying {action} with {agent_name}")
                            bus.send("MissionLead", agent_name, action)
                    else:
                        logger.log(
                            "MissionLead",
                            f"Received failure for {failure_action} from {sender} during {action}",
                        )
                elif isinstance(content, str) and content.startswith("SYSTEM_FAILURE:"):
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
    threading.Thread(target=lead.run, args=(mission,), daemon=True).start()

    launch_dashboard()

    print("Dashboard running at http://localhost:{}".format(os.getenv("DASHBOARD_PORT", "5000")))
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down AERUM controllers...")
