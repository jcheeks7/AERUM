class MissionLead:
    """
    The MissionLead agent is responsible for high-level planning and mission oversight.
    It communicates with other crew agents and monitors the mission timeline.
    """

    def __init__(self, mission_objective):
        """
        Initialize the MissionLead with a specific mission objective.
        
        Parameters:
            mission_objective (str): Description of the current mission (e.g., 'debris_removal')
        """
        self.mission_objective = mission_objective
        self.status = "initialized"
        self.timeline = []
        self.crew = {}

    def register_crew_member(self, role, agent_object):
        """
        Add another AI agent to the mission crew.

        Parameters:
            role (str): Role of the agent (e.g., 'orbital_engineer')
            agent_object (object): Instance of the agent class
        """
        self.crew[role] = agent_object

    def create_mission_timeline(self):
        """
        Create a mock mission timeline.
        This would eventually come from a mission planner or simulation engine.
        """
        self.timeline = [
            {"t": 0, "action": "boot_all_systems"},
            {"t": 10, "action": "scan_environment"},
            {"t": 20, "action": "calculate_maneuver"},
            {"t": 30, "action": "execute_maneuver"},
            {"t": 40, "action": "report_status"},
        ]
        self.status = "timeline_created"

    def execute_mission(self):
        """
        Execute steps in the mission timeline.
        For now, it just prints the steps — but later it'll call the correct agents.
        """
        print(f"[MissionLead] Starting mission: {self.mission_objective}")
        for event in self.timeline:
            print(f"[t={event['t']}] Action: {event['action']}")
        self.status = "mission_executed"
