import json
import os
import threading
import time
from pathlib import Path
from typing import Optional

from flask import Flask, Response, jsonify, request, stream_with_context

from .event_store import EventStore, event_store
from .runtime_controller import RuntimeController


def _load_static_page() -> str:
    """Return the HTML for the dashboard."""

    return (
        Path(__file__).with_name("dashboard.html").read_text()
        if Path(__file__).with_name("dashboard.html").exists()
        else _DEFAULT_HTML
    )


class _StoreOnlyController:
    """Fallback controller that only exposes read-only state."""

    def __init__(self, store: EventStore):
        self._store = store

    def list_missions(self):  # pragma: no cover - simple fallback
        return []

    def get_state_snapshot(self):
        return self._store.get_state_snapshot()

    def start_boot(self):  # pragma: no cover - simple fallback
        return False, "Runtime controller unavailable"

    def start_mission(self, _: str):  # pragma: no cover - simple fallback
        return False, "Runtime controller unavailable"


def create_app(
    store: Optional[EventStore] = None,
    controller: Optional[RuntimeController] = None,
) -> Flask:
    store = store or event_store
    controller = controller or _StoreOnlyController(store)
    base_dir = Path(__file__).parent
    app = Flask(__name__, static_folder=str(base_dir), static_url_path="/ui")

    page_cache = {"html": _load_static_page()}

    @app.route("/")
    def index() -> str:
        return page_cache["html"]

    @app.route("/api/events")
    def api_events() -> Response:
        limit_param = request.args.get("limit")
        offset_param = request.args.get("offset")
        try:
            limit = int(limit_param) if limit_param is not None else 200
        except ValueError:
            limit = 200
        try:
            offset = int(offset_param) if offset_param is not None else 0
        except ValueError:
            offset = 0
        return jsonify({"events": store.get_events(limit=limit, offset=offset)})

    @app.route("/api/agents")
    def api_agents() -> Response:
        return jsonify({"agents": store.get_statuses()})

    @app.route("/api/state")
    def api_state() -> Response:
        return jsonify(controller.get_state_snapshot())

    @app.route("/api/missions")
    def api_missions() -> Response:
        return jsonify({"missions": controller.list_missions()})

    @app.route("/api/boot", methods=["POST"])
    def api_boot() -> Response:
        success, message = controller.start_boot()
        status = 202 if success else 400
        return jsonify({"success": success, "message": message}), status

    @app.route("/api/missions/select", methods=["POST"])
    def api_mission_select() -> Response:
        payload = request.get_json(silent=True) or {}
        filename = payload.get("filename")
        if not filename:
            return jsonify({"success": False, "message": "filename is required"}), 400
        success, message = controller.start_mission(filename)
        status = 202 if success else 400
        return jsonify({"success": success, "message": message}), status

    @app.route("/api/stream")
    def api_stream() -> Response:
        def generate():
            subscriber = store.subscribe()
            try:
                while True:
                    payload = subscriber.get()
                    yield f"data: {json.dumps(payload)}\n\n"
            finally:
                store.unsubscribe(subscriber)

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


def launch_dashboard(
    store: Optional[EventStore] = None,
    controller: Optional[RuntimeController] = None,
) -> threading.Thread:
    """Start the dashboard web server in a background thread."""

    store = store or event_store
    app = create_app(store, controller=controller)
    port = int(os.getenv("DASHBOARD_PORT", "5000"))

    def run_app():
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

    thread = threading.Thread(target=run_app, daemon=True)
    thread.start()
    # Allow Flask to bind before returning to reduce connection errors in tests
    time.sleep(0.2)
    return thread


_DEFAULT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>AERUM Mission Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #0b1120; color: #e2e8f0; }
        header { padding: 16px 24px; background: #1e293b; box-shadow: 0 2px 6px rgba(0,0,0,0.4); }
        h1 { margin: 0; font-size: 1.6rem; }
        main { display: flex; gap: 24px; padding: 24px; }
        section { background: #111827; border-radius: 12px; padding: 16px; flex: 1; overflow: hidden; }
        #timeline { max-height: 70vh; overflow-y: auto; }
        .event { border-bottom: 1px solid rgba(148, 163, 184, 0.2); padding: 12px 0; }
        .event:last-child { border-bottom: none; }
        .event .meta { font-size: 0.85rem; color: #94a3b8; margin-bottom: 4px; }
        .event .message { font-size: 1rem; }
        #agent-panels { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
        .agent-card { background: #0f172a; border-radius: 10px; padding: 12px 16px; border: 1px solid rgba(148, 163, 184, 0.15); }
        .agent-card h3 { margin: 0 0 4px; font-size: 1.1rem; }
        .agent-card .status { font-size: 0.95rem; }
        .agent-card .timestamp { font-size: 0.8rem; color: #64748b; margin-top: 6px; }
        .status-pill { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; margin-left: 8px; }
        .status-active { background: rgba(34,197,94,0.2); color: #4ade80; }
        .status-fault { background: rgba(248,113,113,0.2); color: #f87171; }
        button { background: #2563eb; color: white; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; }
        button:hover { background: #1d4ed8; }
        #controls { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
        #controls h2 { margin: 0; font-size: 1.2rem; }
    </style>
</head>
<body>
    <header>
        <h1>📡 AERUM Mission Control Dashboard</h1>
        <p>Timeline of events and live agent status updates.</p>
    </header>
    <main>
        <section>
            <div id="controls">
                <h2>Event Timeline</h2>
                <button id="refresh-btn">Refresh</button>
            </div>
            <div id="timeline"></div>
        </section>
        <section>
            <h2>Agent Status</h2>
            <div id="agent-panels"></div>
        </section>
    </main>
    <script>
        const timelineEl = document.getElementById('timeline');
        const agentPanelsEl = document.getElementById('agent-panels');
        const refreshBtn = document.getElementById('refresh-btn');

        function renderEvent(event) {
            const wrapper = document.createElement('div');
            wrapper.className = 'event';
            wrapper.innerHTML = `
                <div class="meta">
                    <strong>${event.agent}</strong> · ${new Date(event.timestamp).toLocaleTimeString()} · ${event.category}
                </div>
                <div class="message">${event.message}</div>
            `;
            return wrapper;
        }

        function renderAgent(agent) {
            const card = document.createElement('div');
            card.className = 'agent-card';
            const isFault = agent.status.toLowerCase().includes('fail');
            const pillClass = isFault ? 'status-fault' : 'status-active';
            const pillText = isFault ? 'Attention' : 'Nominal';
            card.innerHTML = `
                <h3>${agent.agent}<span class="status-pill ${pillClass}">${pillText}</span></h3>
                <div class="status">${agent.status}</div>
                <div class="timestamp">Updated ${new Date(agent.timestamp).toLocaleTimeString()}</div>
            `;
            return card;
        }

        function refreshData() {
            fetch('/api/events?limit=200')
                .then(res => res.json())
                .then(data => {
                    timelineEl.innerHTML = '';
                    data.events.forEach(event => {
                        timelineEl.appendChild(renderEvent(event));
                    });
                });

            fetch('/api/agents')
                .then(res => res.json())
                .then(data => {
                    agentPanelsEl.innerHTML = '';
                    data.agents.forEach(agent => {
                        agentPanelsEl.appendChild(renderAgent(agent));
                    });
                });
        }

        function connectStream() {
            const source = new EventSource('/api/stream');
            source.onmessage = (event) => {
                const payload = JSON.parse(event.data);
                if (payload.type === 'event') {
                    const entry = renderEvent(payload.event);
                    timelineEl.insertBefore(entry, timelineEl.firstChild);
                }
                if (payload.type === 'status') {
                    refreshData();
                }
            };
            source.onerror = () => {
                source.close();
                setTimeout(connectStream, 2000);
            };
        }

        refreshBtn.addEventListener('click', refreshData);
        refreshData();
        connectStream();
    </script>
</body>
</html>
"""

