const API_BASE = "";
const POLL_INTERVAL = 1500;

const elements = {
    missionSelect: document.getElementById("missionSelect"),
    startMission: document.getElementById("startMission"),
    pauseMission: document.getElementById("pauseMission"),
    resumeMission: document.getElementById("resumeMission"),
    abortMission: document.getElementById("abortMission"),
    injectFault: document.getElementById("injectFault"),
    currentStep: document.getElementById("currentStep"),
    nextStep: document.getElementById("nextStep"),
    stepDescription: document.getElementById("stepDescription"),
    missionTime: document.getElementById("missionTime"),
    missionMode: document.getElementById("missionMode"),
    faultFlags: document.getElementById("faultFlags"),
    logWindow: document.getElementById("logWindow"),
    agentFilter: document.getElementById("agentFilter"),
    modalOverlay: document.getElementById("modalOverlay"),
    faultAgent: document.getElementById("faultAgent"),
    faultType: document.getElementById("faultType"),
    faultMessage: document.getElementById("faultMessage"),
};

let logs = [];
let agents = [];
let statusSnapshot = null;
let logSocket = null;
const expandedAgents = new Set();

function formatTime(value) {
    const date = value instanceof Date ? value : new Date(value);
    return date.toLocaleTimeString("en-US", { hour12: false });
}

function updateClock() {
    elements.missionTime.textContent = formatTime(new Date());
}
setInterval(updateClock, 1000);
updateClock();

async function fetchJSON(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Request failed: ${response.status}`);
    }
    return response.json();
}

async function loadMissions() {
    try {
        const missions = await fetchJSON("/api/missions");
        elements.missionSelect.innerHTML = missions
            .map((mission) => `<option value="${mission.file}">${mission.name}</option>`)
            .join("");
    } catch (err) {
        console.error("Failed to load missions", err);
    }
}

function renderAgents(agentList) {
    const container = document.getElementById("agents");
    container.innerHTML = "";

    agentList.forEach((agent) => {
        const card = document.createElement("div");
        const health = (agent.health || "GREEN").toLowerCase();
        const expanded = expandedAgents.has(agent.name);
        card.className = `agent-card ${health} ${expanded ? "expanded" : ""}`;
        card.innerHTML = `
            <div class="header">
                <div class="name">${agent.name}</div>
                <div class="health ${health}">${agent.health || "GREEN"}</div>
            </div>
            <div class="state">${agent.status || "Idle"}</div>
            <div class="last-message">Last: ${agent.last_message || "-"}</div>
            <div class="agent-details">
                <div>Details: ${(agent.state && JSON.stringify(agent.state)) || "n/a"}</div>
            </div>
        `;

        card.addEventListener("click", () => {
            if (expandedAgents.has(agent.name)) {
                expandedAgents.delete(agent.name);
            } else {
                expandedAgents.add(agent.name);
            }
            renderAgents(agentList);
        });

        container.appendChild(card);
    });
}

function renderLogs(entries) {
    const filter = elements.agentFilter.value;
    const atBottom =
        Math.abs(elements.logWindow.scrollTop + elements.logWindow.clientHeight - elements.logWindow.scrollHeight) < 8;

    elements.logWindow.innerHTML = "";
    entries
        .filter((entry) => filter === "all" || entry.agent === filter)
        .forEach((entry) => {
            const row = document.createElement("div");
            row.className = `log-entry ${entry.category === "fault" ? "warning" : ""}`;
            row.innerHTML = `
                <div class="timestamp">${formatTime(entry.timestamp)}</div>
                <div class="agent">${entry.agent}</div>
                <div class="message">${entry.message}</div>
            `;
            elements.logWindow.appendChild(row);
        });

    if (atBottom) {
        elements.logWindow.scrollTop = elements.logWindow.scrollHeight;
    }
}

function updateMissionViewer(status) {
    const current = status?.current_step;
    const next = status?.next_step;
    const missionStatus = (status?.status || "IDLE").toUpperCase();

    elements.missionMode.textContent = missionStatus;
    elements.currentStep.textContent = current?.name || current?.action || "Awaiting start";
    elements.stepDescription.textContent = current
        ? `${current.name || current.action} : ${current.detail || current.status || "Executing"}`
        : "Initialize mission to begin";
    elements.nextStep.textContent = next?.name || next?.action || "-";
    elements.faultFlags.textContent = missionStatus === "ABORTED" ? "Abort requested" : "None";
}

async function refreshData() {
    try {
        const [status, agentState, logEntries] = await Promise.all([
            fetchJSON("/api/status"),
            fetchJSON("/api/agents"),
            fetchJSON("/api/logs?limit=200"),
        ]);
        statusSnapshot = status;
        agents = agentState;
        logs = logEntries;
        updateMissionViewer(statusSnapshot);
        renderAgents(agents);
        renderLogs(logs);
        updateAgentFilterOptions(agentState);
    } catch (err) {
        console.error("Failed to refresh data", err);
    }
}

function updateAgentFilterOptions(agentList) {
    const seen = new Set();
    agentList.forEach((agent) => seen.add(agent.name));
    const current = elements.agentFilter.value;
    elements.agentFilter.innerHTML = '<option value="all">All</option>' +
        Array.from(seen)
            .map((name) => `<option value="${name}">${name}</option>`)
            .join("");
    if (current && seen.has(current)) {
        elements.agentFilter.value = current;
    }
}

elements.agentFilter.addEventListener("change", () => renderLogs(logs));

elements.startMission.addEventListener("click", async () => {
    const mission = elements.missionSelect.value;
    if (!mission) return;
    try {
        const status = await fetchJSON("/api/missions/start", {
            method: "POST",
            body: JSON.stringify({ mission_name: mission }),
        });
        statusSnapshot = status;
        updateMissionViewer(statusSnapshot);
    } catch (err) {
        alert(`Unable to start mission: ${err.message}`);
    }
});

elements.pauseMission.addEventListener("click", async () => {
    try {
        const status = await fetchJSON("/api/missions/pause", { method: "POST" });
        statusSnapshot = status;
        updateMissionViewer(statusSnapshot);
    } catch (err) {
        alert(`Unable to pause: ${err.message}`);
    }
});

elements.resumeMission.addEventListener("click", async () => {
    try {
        const status = await fetchJSON("/api/missions/resume", { method: "POST" });
        statusSnapshot = status;
        updateMissionViewer(statusSnapshot);
    } catch (err) {
        alert(`Unable to resume: ${err.message}`);
    }
});

elements.abortMission.addEventListener("click", async () => {
    try {
        const status = await fetchJSON("/api/missions/abort", { method: "POST" });
        statusSnapshot = status;
        updateMissionViewer(statusSnapshot);
    } catch (err) {
        alert(`Unable to abort: ${err.message}`);
    }
});

elements.injectFault.addEventListener("click", () => toggleModal(true));
document.getElementById("closeModal").addEventListener("click", () => toggleModal(false));
elements.modalOverlay.addEventListener("click", (e) => {
    if (e.target === e.currentTarget) toggleModal(false);
});

document.getElementById("submitFault").addEventListener("click", async () => {
    const payload = {
        target_agent: elements.faultAgent.value,
        fault_type: elements.faultType.value,
        details: { note: elements.faultMessage.value.trim() },
    };
    try {
        await fetchJSON("/api/faults/inject", {
            method: "POST",
            body: JSON.stringify(payload),
        });
        toggleModal(false);
        refreshData();
    } catch (err) {
        alert(`Unable to inject fault: ${err.message}`);
    }
});

function toggleModal(show) {
    elements.modalOverlay.classList.toggle("active", show);
    elements.modalOverlay.setAttribute("aria-hidden", !show);
    if (show) {
        elements.faultMessage.value = "";
        elements.faultMessage.focus();
    }
}

function connectLogSocket() {
    try {
        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        logSocket = new WebSocket(`${protocol}://${window.location.host}/ws/logs`);
        logSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data?.event) {
                logs.unshift(data.event);
                renderLogs(logs.slice(0, 200));
            }
        };
        logSocket.onclose = () => {
            logSocket = null;
        };
    } catch (err) {
        console.warn("WebSocket unavailable, falling back to polling", err);
    }
}

async function init() {
    await loadMissions();
    await refreshData();
    connectLogSocket();
    setInterval(refreshData, POLL_INTERVAL);
}

init();
