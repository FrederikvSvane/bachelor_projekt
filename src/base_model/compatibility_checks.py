from typing import Set

from attribute_enum import Attribute
from case import Case
from judge import Judge
from room import Room

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