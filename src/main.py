import os
import time

from interface.dashboard import launch_dashboard
from interface.runtime_controller import RuntimeController


def run_boot_sequence(logger, bus, timeout=5):
    """Sequentially boot subsystems with retry handling (legacy helper)."""

    subsystems = ["power", "comms"]
    required_agents = ["SpacecraftTechnician", "SystemMonitor"]

    for subsystem in subsystems:
        action = f"boot_{subsystem}"
        while bus.fetch("MissionLead"):
            pass
        logger.log("MissionLead", f"Action: {action}")
        for agent in required_agents:
            bus.send("MissionLead", agent, action)
        start = time.time()
        acknowledgements = set()
        failure_reason = None
        while time.time() - start < timeout and acknowledgements != set(required_agents):
            messages = bus.fetch("MissionLead")
            for message in messages:
                sender = message.get("from")
                content = message.get("content", "")
                if isinstance(content, str) and content == f"TASK_COMPLETE: {action}":
                    acknowledgements.add(sender)
                    logger.log("MissionLead", f"Acknowledged {action} by {sender}")
                elif isinstance(content, str) and content.startswith("FAILURE:"):
                    payload = content.split("FAILURE:", 1)[1].strip()
                    failure_action, _, reason = payload.partition("|")
                    failure_action = failure_action.strip()
                    reason = reason.strip() or "unknown"
                    if failure_action == action:
                        failure_reason = reason
                        agent_name = sender or "Unknown"
                        logger.log(
                            "MissionLead",
                            f"Failure reported by {agent_name} for {action}: {reason}",
                        )
                        if sender in acknowledgements:
                            acknowledgements.remove(sender)
                        if sender:
                            logger.log("MissionLead", f"Retrying {action} with {agent_name}")
                            bus.send("MissionLead", sender, action)
                    else:
                        logger.log(
                            "MissionLead",
                            f"Received failure for {failure_action} from {sender} during {action}",
                        )
                elif isinstance(content, str) and content.startswith("SYSTEM_FAILURE:"):
                    failure = content.split(":", 1)[1].strip()
                    if failure == subsystem:
                        logger.log("MissionLead", f"Boot failure detected: {failure}")
                        fix_cmd = f"fix_{failure}"
                        logger.log("MissionLead", f"Delegating fix: {fix_cmd}")
                        for agent in required_agents:
                            bus.send("MissionLead", agent, fix_cmd)
            time.sleep(0.1)

        if acknowledgements != set(required_agents):
            missing = set(required_agents) - acknowledgements
            logger.log(
                "MissionLead",
                f"Boot incomplete. Missing acknowledgements from: {', '.join(missing)}",
            )
            if failure_reason:
                logger.log("MissionLead", f"Last failure reason: {failure_reason}")
            return False

    logger.log("MissionLead", "All systems nominal.")
    return True


def main() -> None:
    controller = RuntimeController()
    launch_dashboard(store=controller.store, controller=controller)

    port = os.getenv("DASHBOARD_PORT", "5000")
    print(f"Dashboard running at http://localhost:{port}")
    print("Open the dashboard to initiate the boot sequence and launch missions.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down AERUM controllers...")


if __name__ == "__main__":
    main()
