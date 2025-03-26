import json
from typing import Dict
from pathlib import Path

from src.base_model.case import Case
from src.base_model.room import Room
from src.base_model.judge import Judge
from src.base_model.meeting import Meeting
from src.base_model.attribute_enum import Attribute

def parse_input(input_path: Path) -> Dict:
    """
    Parse the input JSON file into a structured data dictionary.
    
    Args:
        input_path: Path to the input JSON file
        
    Returns:
        Dictionary containing parsed data
    """
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    # Extract basic parameters
    parsed_data = {
        "work_days": data.get("work_days", 5),  # Default to 5 work days
        "min_per_work_day": data.get("min_per_work_day", 390),  # Default to 8 hours
        "granularity": data.get("granularity", 5)  # Default to 15-minute slots
    }
    
    # Parse cases
    cases = []
    for case in data["cases"]:
        case_attr = Attribute.from_string(case["type"])
        characteristics = {case_attr}
        judge_requirements = {case_attr}  # Judge must have this skill
        room_requirements = set()  # Default no special room requirements
        
        # Add virtual or physical characteristic based on the virtual flag
        if case["virtual"]:
            characteristics.add(Attribute.VIRTUAL)
            judge_requirements.add(Attribute.VIRTUAL)
            room_requirements.add(Attribute.VIRTUAL)
            
        # Add security requirements if needed
        if case.get("security", False):
            if not case["virtual"]:
                characteristics.add(Attribute.SECURITY)
                room_requirements.add(Attribute.SECURITY)
            
        case = Case(
            case_id=case["id"],
            characteristics=characteristics,
            judge_requirements=judge_requirements,
            room_requirements=room_requirements,
            meetings=[Meeting(meeting_id=meeting["id"], meeting_duration=meeting["duration"], duration_of_stay=0 , judge=None, room=None, case=None) for meeting in case["meetings"]]
        )
        cases.append(case)
        
        for case in cases:
            for meeting in case.meetings:
                meeting.case = case
        
        
    
    # Parse judges
    judges = []
    for judge in data["judges"]:
        skills = [Attribute.from_string(skill) for skill in judge["skills"]]
        characteristics = set(skills)
        case_requirements = set()
        room_requirements = set()
        
        # Add virtual or physical characteristic based on the virtual flag
        if judge["virtual"]:
            characteristics.add(Attribute.VIRTUAL)
            
        # Add accessibility requirement if needed
        if judge.get("accessibility", False):
            characteristics.add(Attribute.ACCESSIBILITY)
            room_requirements.add(Attribute.ACCESSIBILITY)
            
        # Add shortduration requirement if judge has health limitations
        if judge.get("shortduration", False):
            characteristics.add(Attribute.SHORTDURATION)
            case_requirements.add(Attribute.SHORTDURATION)
            
        judge = Judge(
            judge_id=judge["id"],
            characteristics=characteristics,
            case_requirements=case_requirements,
            room_requirements=room_requirements
        )

        judges.append(judge)
    
    # Parse rooms
    rooms = []
    for room in data["rooms"]:
        characteristics = set()
        case_requirements = set()
        judge_requirements = set()
        
        # Add virtual or physical characteristic based on the virtual flag
        if room["virtual"]:
            characteristics.add(Attribute.VIRTUAL)
            
        # Add accessibility if room has it
        if room.get("accessibility", False):
            characteristics.add(Attribute.ACCESSIBILITY)
            
        # Add security if room has it
        if room.get("security", False):
            if not room["virtual"]:
                characteristics.add(Attribute.SECURITY)
            
        room = Room(
            room_id=room["id"],
            characteristics=characteristics,
            case_requirements=case_requirements,
            judge_requirements=judge_requirements
        )

        rooms.append(room)
    
    # Add to parsed data
    parsed_data["cases"] = cases
    parsed_data["judges"] = judges
    parsed_data["rooms"] = rooms
    
    # Print summary of parsed data
    print(f"Parsed {len(cases)} cases, {len(judges)} judges, {len(rooms)} rooms")
    
    return parsed_data