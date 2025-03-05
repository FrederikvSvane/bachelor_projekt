import json
from typing import Dict, List, Any
from pathlib import Path

from src.model import Case, Judge, Room, Attribute

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
        "min_per_work_day": data.get("min_per_work_day", 480),  # Default to 8 hours
        "granularity": data.get("granularity", 15)  # Default to 15-minute slots
    }
    
    # Parse cases
    cases = []
    for i, case_data in enumerate(data.get("cases", [])):
        case_type_str = case_data.get("type", "Civile")
        try:
            case_type = Attribute.from_string(case_type_str)
        except ValueError:
            print(f"Warning: Invalid case type '{case_type_str}', defaulting to Civile")
            case_type = Attribute.CIVILE
        
        case = Case(
            case_id=case_data.get("id", i),
            case_duration=case_data.get("duration", 60),
            case_Attribute=case_type,
            case_virtual=case_data.get("virtual", False)
        )
        cases.append(case)
    
    # Parse judges
    judges = []
    for i, judge_data in enumerate(data.get("judges", [])):
        # Parse skills
        skills = []
        for skill_str in judge_data.get("skills", ["Civile"]):
            try:
                skill = Attribute.from_string(skill_str)
                skills.append(skill)
            except ValueError:
                print(f"Warning: Invalid judge skill '{skill_str}', skipping")
        
        # Ensure judge has at least one skill
        if not skills:
            print(f"Warning: Judge {i} has no valid skills, adding default Civile")
            skills.append(Attribute.CIVILE)
        
        judge = Judge(
            judge_id=judge_data.get("id", i),
            judge_skills=skills,
            judge_virtual=judge_data.get("virtual", False)
        )
        judges.append(judge)
    
    # Parse rooms
    rooms = []
    for i, room_data in enumerate(data.get("rooms", [])):
        room = Room(
            room_id=room_data.get("id", i),
            room_virtual=room_data.get("virtual", False)
        )
        rooms.append(room)
    
    # Add to parsed data
    parsed_data["cases"] = cases
    parsed_data["judges"] = judges
    parsed_data["rooms"] = rooms
    
    # Print summary of parsed data
    print(f"Parsed {len(cases)} cases, {len(judges)} judges, {len(rooms)} rooms")
    
    return parsed_data