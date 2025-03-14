from typing import List, Dict

from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.compatibility_checks import (case_requires_from_judge, judge_requires_from_case,
                                                case_room_compatible, judge_room_compatible)

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
        remainders = [
            (judge.judge_id, float_capacities[judge.judge_id] - int_capacities[judge.judge_id])
            for judge in judges if float_capacities[judge.judge_id] > 0
        ]
        for _ in range(remaining):
            remainders.sort(key=lambda x: x[1], reverse=True)
            judge_id, remainder = remainders[0]
            int_capacities[judge_id] += 1
            remainders[0] = (judge_id, remainder - 1.0)
    
    return int_capacities


def calculate_all_room_capacities(jc_pairs, rooms: list[Room]) -> dict[int, int]:
    """
    Calculate the capacities of all rooms such that the sum of their capacities 
    equals the total number of cases.
    
    Args:
        cases: List of Case objects
        rooms: List of Room objects
    
    Returns:
        Dict[int, int]: A dictionary mapping each room's ID to their calculated capacity.
    """
    # Group case_judge pairs by their room requirements
    requirement_groups = {}
    for jc_pair in jc_pairs:
        # Combine requirements from both case and judge
        combined_req = frozenset(
            list(jc_pair.case.room_requirements) + 
            list(jc_pair.judge.room_requirements)
        )
        if combined_req not in requirement_groups:
            requirement_groups[combined_req] = []
        requirement_groups[combined_req].append(jc_pair)
    
    
    # Count cases per requirement group
    group_counts = {req: len(pairs_list) for req, pairs_list in requirement_groups.items()}
    
    # Calculate weights for each room per requirement group
    room_weights = {}
    for room in rooms:
        room_weights[room.room_id] = {}
        for req_group, pairs_in_group in requirement_groups.items():
            # Check compatibility against the first case in the group
            if pairs_in_group:
                sample_pair = pairs_in_group[0]
                # Use one-directional compatibility checks
                compatible = (case_room_compatible(sample_pair.get_case(), room) and judge_room_compatible(sample_pair.get_judge(), room))
            else:
                compatible = False

            competing_rooms = sum(1 for r in rooms if 
                                case_room_compatible(sample_pair.case, r) and 
                                judge_room_compatible(sample_pair.judge, r))

            
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
    total_pairs = len(jc_pairs)
    current_sum = sum(int_capacities.values())
    remaining = total_pairs - current_sum
    
    if remaining > 0:
        # Sort rooms by fractional remainder
        remainders = [(r.room_id, float_capacities[r.room_id] - int_capacities[r.room_id]) 
                     for r in rooms if float_capacities[r.room_id] > 0]
        
        # Add one case to rooms with largest remainders
        for _ in range(remaining):
            remainders.sort(key=lambda x: x[1], reverse=True)
            room_id, remainder = remainders[0]
            int_capacities[room_id] += 1
            remainders[0] = (room_id, remainder - 1.0)
    
    # Safety check - ensure all cases are assigned
    if sum(int_capacities.values()) != total_pairs:
        print(f"Warning: Room capacity calculation did not distribute all cases. " +
              f"Assigned: {sum(int_capacities.values())}, Total: {total_pairs}")
        
        # Find room with highest capacity and add the difference
        if rooms:
            max_room = max(rooms, key=lambda r: float_capacities[r.room_id])
            int_capacities[max_room.room_id] += (total_pairs - sum(int_capacities.values()))
    
    return int_capacities