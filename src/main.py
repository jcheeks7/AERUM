from agents.mission_lead import MissionLead

if __name__ == "__main__":
    lead = MissionLead("debris_removal")
    lead.create_mission_timeline()
    lead.execute_mission()
