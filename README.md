# AERUM – Autonomous Embedded Reasoning Unit for Missions

AERUM simulates a small astronaut crew of cooperative agents that coordinate through a shared message bus to execute mission scripts. The project is structured to make it easy to embed on constrained hardware, extend with new agents, and connect to the live web dashboard.

## Architecture overview

```
aerum/
├─ core/
│  ├─ controller.py     # AERUMController orchestrating boot + missions
│  ├─ mission_engine.py # Mission loader/step tracker
│  ├─ message_bus.py    # Lightweight intra-agent queue
│  └─ config.py         # Paths + runtime settings
├─ agents/
│  ├─ base_agent.py
│  ├─ mission_lead.py
│  ├─ orbital_engineer.py
│  ├─ mission_specialist.py
│  ├─ monitoring_agent.py
│  └─ spacecraft_technician.py
├─ io/
│  ├─ logger.py         # Text log writer
│  └─ event_store.py    # In-memory state/events for dashboards
├─ missions/            # JSON mission scripts
├─ utils/planner.py     # Condition/retry helpers for agent actions
├─ web/                 # Dashboard frontend assets
scripts/run_mission.py  # CLI entry point
backend/server.py       # FastAPI dashboard API
```

Key runtime components:
- **AERUMController**: manages boot sequencing, mission lifecycle, agent registry, and state exposure for APIs.
- **MessageBus**: simple queue supporting directed and broadcast messages between agents.
- **MissionEngine**: loads JSON missions and tracks current/next steps.
- **Logger + EventStore**: persistent log file plus in-memory stream used by the dashboard/WebSocket feed.

## Quickstart

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run an example mission from the CLI:
   ```bash
   python scripts/run_mission.py --mission debris_removal.json
   ```
3. Launch the dashboard backend and UI:
   ```bash
   uvicorn backend.server:app --reload
   ```
   Then open http://localhost:8000/ to view the dashboard (assets served from `/ui`).

## Missions

Mission scripts live in `aerum/missions/` and follow a simple schema:
```json
[
  {"step": 1, "agent": "MissionLead", "message": "Initialize systems"},
  {"step": 2, "agent": "OrbitalEngineer", "message": "Stabilize attitude"},
  {"step": 3, "agent": "MissionSpecialist", "message": "Run diagnostics"}
]
```
Add new missions by placing JSON files in this directory; they are automatically discovered by the API and CLI.

## Dashboard API mapping

The FastAPI service in `backend/server.py` exposes:
- `GET /api/missions` – list available missions.
- `POST /api/missions/start|pause|resume|abort` – lifecycle controls.
- `GET /api/status` – mission/step/progress snapshot.
- `GET /api/agents` – summarized agent health and state.
- `GET /api/logs` – recent log events; `WS /ws/logs` streams live events.

The web UI (in `aerum/web/`) polls these endpoints to stay synchronized with the running controller.
