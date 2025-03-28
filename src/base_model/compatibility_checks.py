from typing import Set

from src.base_model.attribute_enum import Attribute
from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.room import Room

# One-directional compatibility check
def has_required_characteristics(requirements: Set[Attribute], 
                               characteristics: Set[Attribute]) -> bool:
    """
    One-way compatibility check: Do the characteristics satisfy the requirements?
    
    Args:
        requirements: The attributes that are required
        characteristics: The attributes that are provided
        
    Returns:
        True if all requirements are satisfied, False otherwise
    """
    return requirements.issubset(characteristics)

def judge_requires_from_room(judge: Judge, room: Room) -> bool:
    """Check if room satisfies judge's requirements (one-way)."""
    return has_required_characteristics(judge.room_requirements, room.characteristics)

def room_requires_from_judge(room: Room, judge: Judge) -> bool:
    """Check if judge satisfies room's requirements (one-way)."""
    return has_required_characteristics(room.judge_requirements, judge.characteristics)

def case_requires_from_judge(case: Case, judge: Judge) -> bool:
    """Check if judge satisfies case's requirements (one-way)."""
    return has_required_characteristics(case.judge_requirements, judge.characteristics)

def judge_requires_from_case(judge: Judge, case: Case) -> bool:
    """Check if case satisfies judge's requirements (one-way)."""
    return has_required_characteristics(judge.case_requirements, case.characteristics)

def case_requires_from_room(case: Case, room: Room) -> bool:
    """Check if room satisfies case's requirements (one-way)."""
    return has_required_characteristics(case.room_requirements, room.characteristics)

def room_requires_from_case(room: Room, case: Case) -> bool:
    """Check if case satisfies room's requirements (one-way)."""
    return has_required_characteristics(room.case_requirements, case.characteristics)


# Bidirectional compatibility check
def is_compatible(entity1_requirements: Set[Attribute], 
                 entity2_characteristics: Set[Attribute]) -> bool:
    """Check if entity2's characteristics satisfy entity1's requirements."""
    return entity1_requirements.issubset(entity2_characteristics)

def case_judge_compatible(case: Case, judge: Judge) -> bool:
    """Check if case and judge are compatible (bidirectional)."""
    return (is_compatible(case.judge_requirements, judge.characteristics) and
            is_compatible(judge.case_requirements, case.characteristics))

def case_room_compatible(case: Case, room: Room) -> bool:
    """Check if case and room are compatible (bidirectional)."""
    return (is_compatible(case.room_requirements, room.characteristics) and
            is_compatible(room.case_requirements, case.characteristics))

def judge_room_compatible(judge: Judge, room: Room) -> bool:
    """Check if judge and room are compatible (bidirectional)."""
    return (is_compatible(judge.room_requirements, room.characteristics) and
            is_compatible(room.judge_requirements, judge.characteristics))

case_judge_matrix = {}
case_room_matrix = {}
judge_room_matrix = {}

def initialize_compatibility_matricies(parsed_data):
    """
    Initialize compatibility matricies for judges, rooms, and cases.
    
    Args:
        parsed_data: Input data json, with judges, rooms, cases and meetings
    """
    global case_judge_matrix, case_room_matrix, judge_room_matrix

    case_judge_matrix.clear()
    case_room_matrix.clear()
    judge_room_matrix.clear()

    cases = parsed_data["cases"]
    judges = parsed_data["judges"]
    rooms = parsed_data["rooms"]

    for case in cases:
        case_id = case.case_id
        case_judge_matrix[case_id] = {}

        for judge in judges:
            judge_id = judge.judge_id
            case_judge_matrix[case_id][judge_id] = case_judge_compatible(case, judge)

    for case in cases:
        case_id = case.case_id
        case_room_matrix[case_id] = {}

        for room in rooms:
            room_id = room.room_id
            case_room_matrix[case_id][room_id] = case_room_compatible(case, room)

    for judge in judges:
        judge_id = judge.judge_id
        judge_room_matrix[judge_id] = {}

        for room in rooms:
            room_id = room.room_id
            judge_room_matrix[judge_id][room_id] = judge_room_compatible(judge, room)
    
    
# Efficient compatibility checks
def check_case_judge_compatibility(case_id: int, judge_id: int) -> bool:
    """
    Efficiently check if a case and judge are compatible, using compatibility matrix.
    Return true if compatible, false otherwise.
    """
    return case_judge_matrix[case_id][judge_id]

def check_case_room_compatibility(case_id: int, room_id: int) -> bool:
    """
    Efficiently check if a case and room are compatible, using compatibility matrix.
    Return true if compatible, false otherwise.
    """
    return case_room_matrix[case_id][room_id]

def check_judge_room_compatibility(judge_id: int, room_id: int) -> bool:
    """
    Efficiently check if a judge and room are compatible, using compatibility matrix.
    Return true if compatible, false otherwise.
    """
    return judge_room_matrix[judge_id][room_id]