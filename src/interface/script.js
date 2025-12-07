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
            card.classList.toggle("expanded");
        });

        container.appendChild(card);
    });
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
