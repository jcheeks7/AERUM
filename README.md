# AERUM – Artificially Emulated Remote Unit Missioncrew

AERUM is an onboard AI crew system designed to autonomously operate satellites through role-based LLM agents.

## Core Features
- Role-specific AI agents (Mission Lead, Orbital Engineer, etc.)
- Autonomous spacecraft operation (simulated & hardware-capable)
- Natural language interface for mission control
- Modular architecture for extension (robotic arms, payloads, etc.)

## Web Dashboard

After the boot sequence completes you will be prompted in the console to select a mission. Once the mission is selected the Flask-powered dashboard starts automatically on `http://localhost:5000` (or the port defined by the `DASHBOARD_PORT` environment variable). The dashboard provides:

- **Timeline of events** with live updates streamed from all agent logs.
- **Agent status panels** summarising the latest message and update time per agent.
- **Manual refresh controls** that can be used while testing without SSE support.

### Running the dashboard locally

```bash
pip install -r requirements.txt
python -m src.main
```

Follow the console prompt to select a mission. Leave the process running to keep the dashboard live. Press `Ctrl+C` to shut the agents and web server down.
