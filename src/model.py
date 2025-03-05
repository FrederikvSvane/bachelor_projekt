from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Set


class Attribute(Enum):
    """ 
    Base enum for all Attributes of entities in the model.
    For example, a case can have Attribute "STRAFFE", if it is a straffe case.
    And a judge can have a Attribute "STRAFFE", if the judge is able to be assigned straffe cases.
    
    This is meant to be as general and extendable as possible, because our own imaginations bottleneck the 
    amount of constraints we are able to formulate between the entities of the model.
    """
    
    # Case-Judge Attributes: 
    # case has type or judge can conduct cases of type
    CIVIL = auto() # bidirectional
    STRAFFE = auto() # bidirectional
    TVANG = auto() # bidirectional
    DOEDSBO = auto() # bidirectional
    GRUNDLOV = auto() # bidirectional
    
    # judge can only conduct short cases (<120min) due to health or case is <120 min
    SHORTDURATION = auto() # one-directional
    
    
    # Case-Room Attributes:
    # impeached is dangerous and requires security or room has facilities for security
    SECURITY = auto() # one-directional
    
    # virtual or physical room or case
    PHYSICAL = auto() # bidirectional
    VIRTUAL = auto() # bidirectional
    
    
    # Judge-Room Attributes:
    # judge requires accessibility or room facilitates accessibility
    ACCESSIBILITY = auto() # one-directional
    
    def __str__(self):
        return self.name.capitalize()
    
    @classmethod
    def from_string(cls, attribute_string: str) -> 'Attribute':
        try:
            return cls[attribute_string.upper()]
        except KeyError:
            raise ValueError(f"No attribute found for: {attribute_string}")
        
    @classmethod
    def to_string(cls, attribute) -> str:
        if not isinstance(attribute, cls):
            raise ValueError(f"Expected an Attribute, got {type(attribute)}")
        return str(attribute)
    
@dataclass
class Case:
    """Class representing a court case"""
    case_id: int
    case_duration: int  # in minutes
    characteristics: Set[Attribute] = field(default_factory=set)
    judge_requirements: Set[Attribute] = field(default_factory=set)
    room_requirements: Set[Attribute] = field(default_factory=set)
    
    def __str__(self):
        char_str = ", ".join(str(char) for char in self.characteristics)
        req_str = ", ".join(str(req) for req in self.judge_requirements)
        return f"Case(id={self.case_id}, duration={self.case_duration}, chars=[{char_str}], reqs=[{req_str}])"

@dataclass
class Judge:
    """Class representing a judge"""
    judge_id: int
    characteristics: Set[Attribute] = field(default_factory=set)
    case_requirements: Set[Attribute] = field(default_factory=set)
    room_requirements: Set[Attribute] = field(default_factory=set)
    
    def __str__(self):
        char_str = ", ".join(str(char) for char in self.characteristics)
        return f"Judge(id={self.judge_id}, chars=[{char_str}])"

@dataclass
class Room:
    """Class representing a court room"""
    room_id: int
    characteristics: Set[Attribute] = field(default_factory=set)
    case_requirements: Set[Attribute] = field(default_factory=set)
    judge_requirements: Set[Attribute] = field(default_factory=set)
    
    def __str__(self):
        char_str = ", ".join(str(char) for char in self.characteristics)
        return f"Room(id={self.room_id}, chars=[{char_str}])"

@dataclass
class Appointment:
    """Class representing a scheduled appointment"""
    case: Case
    judge: Judge
    room: Room
    day: int
    timeslot_start: int
    timeslots_duration: int
    
    def __str__(self):
        return (f"Appointment(case_id={self.case.case_id}, "
                f"judge_id={self.judge.judge_id}, room_id={self.room.room_id}, "
                f"day={self.day}, start={self.timeslot_start}, "
                f"duration={self.timeslots_duration})")
        
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



def calculate_all_judge_capacities(cases: List[Case], judges: List[Judge]) -> Dict[int, int]:
    """
    Calculate the capacities of all judges such that the sum of their weighted capacities equals the total number of cases.

    Args:
        Cases: List of Case objects to distribute.
        Judges: List of Judge objects to distribute among.

    Returns:
        Dict[int, int]: A dictionary mapping each judge's ID to their calculated capacity.
    """
    # Group cases by their judge requirements
    requirement_groups = {}
    for case in cases:
        req_key = frozenset(case.judge_requirements)
        if req_key not in requirement_groups:
            requirement_groups[req_key] = []
        requirement_groups[req_key].append(case)
    
    # Count cases per requirement group
    group_counts = {req: len(cases_list) for req, cases_list in requirement_groups.items()}
    
    # Calculate weights for each judge per requirement group
    judge_weights = {}
    for judge in judges:
        judge_weights[judge.judge_id] = {}
        for req_group, cases_in_group in requirement_groups.items():
            # Check compatibility against the first case in the group
            if cases_in_group:
                sample_case = cases_in_group[0]
                # Use one-directional compatibility checks
                compatible = (case_requires_from_judge(sample_case, judge) and 
                             judge_requires_from_case(judge, sample_case))
            else:
                compatible = False
            
            # Calculate how many judges can handle this group
            competing_judges = sum(1 for j in judges if 
                                 case_requires_from_judge(sample_case, j) and 
                                 judge_requires_from_case(j, sample_case))
            
            # Weight is inversely proportional to number of judges that can handle this group
            weight = 1.0 / max(1, competing_judges) if compatible else 0
            judge_weights[judge.judge_id][req_group] = weight
    
    # Calculate floating-point capacities for each judge
    float_capacities = {}
    for judge in judges:
        capacity = 0.0
        for req_group, count in group_counts.items():
            weight = judge_weights[judge.judge_id][req_group]
            # For each requirement group, distribute cases based on weight
            capacity += weight * count
        float_capacities[judge.judge_id] = capacity
    
    # Convert to integer capacities (floor values)
    int_capacities = {judge_id: int(cap) for judge_id, cap in float_capacities.items()}
    
    # Distribute remaining cases using largest remainder method
    total_cases = len(cases)
    current_sum = sum(int_capacities.values())
    remaining = total_cases - current_sum
    
    if remaining > 0:
        # Sort judges by fractional remainder
        remainders = [(j.judge_id, float_capacities[j.judge_id] - int_capacities[j.judge_id]) 
                     for j in judges]
        remainders.sort(key=lambda x: x[1], reverse=True)
        
        # Add one case to judges with largest remainders
        for i in range(remaining):
            if i < len(remainders):
                judge_id = remainders[i][0]
                int_capacities[judge_id] += 1
    
    return int_capacities


def calculate_all_room_capacities(cases: List[Case], rooms: List[Room]) -> Dict[int, int]:
    """
    Calculate the capacities of all rooms such that the sum of their capacities 
    equals the total number of cases.
    
    Args:
        cases: List of Case objects
        rooms: List of Room objects
    
    Returns:
        Dict[int, int]: A dictionary mapping each room's ID to their calculated capacity.
    """
    # Group cases by their room requirements
    requirement_groups = {}
    for case in cases:
        req_key = frozenset(case.room_requirements)
        if req_key not in requirement_groups:
            requirement_groups[req_key] = []
        requirement_groups[req_key].append(case)
    
    # Count cases per requirement group
    group_counts = {req: len(cases_list) for req, cases_list in requirement_groups.items()}
    
    # Calculate weights for each room per requirement group
    room_weights = {}
    for room in rooms:
        room_weights[room.room_id] = {}
        for req_group, cases_in_group in requirement_groups.items():
            # Check compatibility against the first case in the group
            if cases_in_group:
                sample_case = cases_in_group[0]
                # Use one-directional compatibility checks
                compatible = (case_requires_from_room(sample_case, room) and 
                             room_requires_from_case(room, sample_case))
            else:
                compatible = False
            
            # Calculate how many rooms can handle this group
            competing_rooms = sum(1 for r in rooms if 
                                case_requires_from_room(sample_case, r) and 
                                room_requires_from_case(r, sample_case))
            
            # Weight is inversely proportional to number of rooms that can handle this group
            weight = 1.0 / max(1, competing_rooms) if compatible else 0
            room_weights[room.room_id][req_group] = weight
    
    # Calculate floating-point capacities for each room
    float_capacities = {}
    for room in rooms:
        capacity = 0.0
        for req_group, count in group_counts.items():
            weight = room_weights[room.room_id][req_group]
            # For each requirement group, distribute cases based on weight
            capacity += weight * count
        float_capacities[room.room_id] = capacity
    
    # Convert to integer capacities (floor values)
    int_capacities = {room_id: int(cap) for room_id, cap in float_capacities.items()}
    
    # Distribute remaining cases using largest remainder method
    total_cases = len(cases)
    current_sum = sum(int_capacities.values())
    remaining = total_cases - current_sum
    
    if remaining > 0:
        # Sort rooms by fractional remainder
        remainders = [(r.room_id, float_capacities[r.room_id] - int_capacities[r.room_id]) 
                     for r in rooms]
        remainders.sort(key=lambda x: x[1], reverse=True)
        
        # Add one case to rooms with largest remainders
        for i in range(remaining):
            if i < len(remainders):  # Safety check for when we have more remaining than rooms
                room_id = remainders[i][0]
                int_capacities[room_id] += 1
    
    # Safety check - ensure all cases are assigned
    if sum(int_capacities.values()) != total_cases:
        print(f"Warning: Room capacity calculation did not distribute all cases. " +
              f"Assigned: {sum(int_capacities.values())}, Total: {total_cases}")
        
        # Find room with highest capacity and add the difference
        if rooms:
            max_room = max(rooms, key=lambda r: float_capacities[r.room_id])
            int_capacities[max_room.room_id] += (total_cases - sum(int_capacities.values()))
    
    return int_capacities