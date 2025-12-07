const API_BASE = "";
const POLL_INTERVAL = 1500;

const elements = {
    missionSelect: document.getElementById("missionSelect"),
    startMission: document.getElementById("startMission"),
    pauseMission: document.getElementById("pauseMission"),
    resumeMission: document.getElementById("resumeMission"),
    abortMission: document.getElementById("abortMission"),
    injectFault: document.getElementById("injectFault"),
const missionSteps = [
    { step: 1, agent: "MissionLead", message: "Initialize systems" },
    { step: 2, agent: "OrbitalEngineer", message: "Stabilize attitude" },
    { step: 3, agent: "MissionSpecialist", message: "Run diagnostics" }
];

const agentsState = {
    MissionLead: {
        name: "MissionLead",
        health: "green",
        status: "Coordinating mission timeline",
        lastMessage: "Awaiting start",
        details: "Supervises mission phases and authorizes transitions."
    },
    OrbitalEngineer: {
        name: "OrbitalEngineer",
        health: "green",
        status: "Guidance nominal",
        lastMessage: "Attitude stable",
        details: "Maintains orbit, attitude, and propulsion sequencing."
    },
    MissionSpecialist: {
        name: "MissionSpecialist",
        health: "green",
        status: "Payload ready",
        lastMessage: "Diagnostics pending",
        details: "Executes payload operations and health assessments."
    }
};

let logEntries = [];
let missionIndex = 0;
let missionTimer = null;
let isRunning = false;
let isPaused = false;

const elements = {
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
    faultMessage: document.getElementById("faultMessage")
};

function formatTime(date) {
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
function renderAgents() {
    const container = document.getElementById("agents");
    container.innerHTML = "";

    Object.values(agentsState).forEach((agent) => {
        const card = document.createElement("div");
        card.className = `agent-card ${agent.health}`;
        card.innerHTML = `
            <div class="header">
                <div class="name">${agent.name}</div>
                <div class="health ${agent.health}">${agent.health}</div>
            </div>
            <div class="state">${agent.status}</div>
            <div class="last-message">Last: ${agent.lastMessage}</div>
            <div class="agent-details">
                <div>Details: ${agent.details}</div>
                <div>Load: ${(Math.random() * 40 + 50).toFixed(0)}%</div>
                <div>Latency: ${(Math.random() * 120 + 20).toFixed(0)} ms</div>
            </div>
        `;

        card.addEventListener("click", () => {
            if (expandedAgents.has(agent.name)) {
                expandedAgents.delete(agent.name);
            } else {
                expandedAgents.add(agent.name);
            }
            renderAgents(agentList);
            card.classList.toggle("expanded");
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
function addLogEntry({ agent, message, type = "standard" }) {
    const entry = {
        timestamp: formatTime(new Date()),
        agent,
        message,
        type
    };
    logEntries.push(entry);
    renderLog();
}

function renderLog() {
    const filter = elements.agentFilter.value;
    elements.logWindow.innerHTML = "";

    logEntries
        .filter((entry) => filter === "all" || entry.agent === filter)
        .forEach((entry) => {
            const div = document.createElement("div");
            div.className = `log-entry ${entry.type !== "standard" ? entry.type : ""}`;
            div.innerHTML = `
                <div class="timestamp">${entry.timestamp}</div>
                <div class="agent">${entry.agent}</div>
                <div class="message">${entry.message}</div>
            `;
            elements.logWindow.appendChild(div);
        });

    elements.logWindow.scrollTop = elements.logWindow.scrollHeight;
}

elements.agentFilter.addEventListener("change", renderLog);

document.getElementById("startMission").addEventListener("click", () => {
    if (isRunning && isPaused) {
        isPaused = false;
        elements.missionMode.textContent = "EXECUTE";
        scheduleNextStep();
        addLogEntry({ agent: "System", message: "Mission resumed", type: "system" });
        return;
    }

    if (isRunning) return;

    isRunning = true;
    isPaused = false;
    missionIndex = 0;
    logEntries = [];
    elements.logWindow.innerHTML = "";
    elements.missionMode.textContent = "EXECUTE";
    elements.faultFlags.textContent = "None";
    updateMissionViewer();
    addLogEntry({ agent: "System", message: "Mission sequence started", type: "system" });
    scheduleNextStep();
});

document.getElementById("pauseMission").addEventListener("click", () => {
    if (!isRunning || isPaused) return;
    isPaused = true;
    clearTimeout(missionTimer);
    elements.missionMode.textContent = "PAUSED";
    addLogEntry({ agent: "System", message: "Mission paused", type: "system" });
});

document.getElementById("abortMission").addEventListener("click", () => {
    if (!isRunning) return;
    isRunning = false;
    isPaused = false;
    clearTimeout(missionTimer);
    addLogEntry({ agent: "System", message: "ABORT signal received", type: "warning" });
    elements.missionMode.textContent = "ABORTED";
    elements.currentStep.textContent = "Mission aborted";
    elements.nextStep.textContent = "-";
    elements.stepDescription.textContent = "Manual restart required";
});

document.getElementById("injectFault").addEventListener("click", () => toggleModal(true));
document.getElementById("closeModal").addEventListener("click", () => toggleModal(false));
document.getElementById("modalOverlay").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) toggleModal(false);
});

document.getElementById("submitFault").addEventListener("click", () => {
    const agent = elements.faultAgent.value;
    const message = elements.faultMessage.value.trim() || "Unspecified fault injected";
    addLogEntry({ agent, message: `FAULT: ${message}`, type: "warning" });
    elements.faultFlags.textContent = `Fault detected: ${agent}`;
    agentsState[agent].health = "yellow";
    agentsState[agent].status = "Investigating anomaly";
    agentsState[agent].lastMessage = message;
    renderAgents();
    toggleModal(false);
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
function scheduleNextStep() {
    clearTimeout(missionTimer);
    if (!isRunning || isPaused) return;

    missionTimer = setTimeout(() => {
        executeStep();
        missionIndex += 1;
        if (missionIndex < missionSteps.length) {
            scheduleNextStep();
        } else {
            isRunning = false;
            elements.missionMode.textContent = "COMPLETE";
            addLogEntry({ agent: "System", message: "Mission complete", type: "system" });
            elements.nextStep.textContent = "-";
        }
    }, 2000);
}

function executeStep() {
    const step = missionSteps[missionIndex];
    if (!step) return;

    const agent = agentsState[step.agent];
    agent.lastMessage = step.message;
    agent.status = "Executing step";
    agent.health = agent.health === "yellow" ? "yellow" : "green";
    renderAgents();

    addLogEntry({ agent: step.agent, message: step.message });
    updateMissionViewer();
}

function updateMissionViewer() {
    const current = missionSteps[missionIndex];
    const next = missionSteps[missionIndex + 1];

    elements.currentStep.textContent = current ? `Step ${current.step}` : "Awaiting start";
    elements.stepDescription.textContent = current ? `${current.agent}: ${current.message}` : "Initialize mission to begin";
    elements.nextStep.textContent = next ? `Step ${next.step} - ${next.message}` : "None";
}

renderAgents();
updateMissionViewer();
