from typing import List, Dict

from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.meeting import Meeting
from src.base_model.compatibility_checks import (case_requires_from_judge, judge_requires_from_case,
                                                case_room_compatible, judge_room_compatible)
def calculate_all_judge_capacities(meetings: list[Meeting], judges: List[Judge]) -> Dict[int, int]:
    """
    Calculate the capacities of all judges such that the sum of their weighted capacities equals the total number of cases.
    Args:
        meetings: List of Meeting objects to distribute.
        judges: List of Judge objects to distribute among.
    Returns:
        Dict[int, int]: A dictionary mapping each judge's ID to their calculated capacity.
    """
    # Group cases by their judge requirements
    requirement_groups = {}
    for meeting in meetings:
        req_key = frozenset(meeting.case.judge_requirements)
        if req_key not in requirement_groups:
            requirement_groups[req_key] = []
        requirement_groups[req_key].append(meeting.case)
    
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
    
    # Track fractional assignments by requirement group
    group_fractional_cases = {}
    for req_group, count in group_counts.items():
        # Calculate how many cases of this type were assigned as integers
        integer_assigned = sum(
            int(judge_weights[j.judge_id][req_group] * count)
            for j in judges
        )
        fractional_remaining = count - integer_assigned
        if fractional_remaining > 0:
            group_fractional_cases[req_group] = fractional_remaining
    
    # Distribute remaining cases by requirement group
    for req_group, remaining_count in group_fractional_cases.items():
        # Get sample case to check compatibility
        sample_case = requirement_groups[req_group][0]
        
        # Get eligible judges for this requirement group
        eligible_judges = []
        for judge in judges:
            # Check if judge can handle this case type
            if judge_weights[judge.judge_id][req_group] > 0:
                fractional_part = (float_capacities[judge.judge_id] - 
                                 int_capacities[judge.judge_id])
                # Only include judges with remainder > 0
                if fractional_part > 0:
                    eligible_judges.append({
                        'judge_id': judge.judge_id,
                        'current_capacity': int_capacities[judge.judge_id],
                        'remainder': fractional_part,
                        'weight_for_group': judge_weights[judge.judge_id][req_group]
                    })
        
        # Sort eligible judges by current capacity (ascending), then remainder (descending)
        eligible_judges.sort(key=lambda x: (x['current_capacity'], -x['remainder']))
        
        # Assign the remaining cases of this type to eligible judges
        assigned = 0
        for eligible_judge in eligible_judges:
            if assigned < remaining_count:
                int_capacities[eligible_judge['judge_id']] += 1
                assigned += 1
                # Update for potential re-sorting if needed
                eligible_judge['current_capacity'] += 1
                eligible_judge['remainder'] -= 1.0
    
    return int_capacities


def calculate_all_room_capacities(jm_pairs, rooms: list[Room]) -> dict[int, int]:
    """
    Calculate the capacities of all rooms such that the sum of their capacities 
    equals the total number of cases.
    
    Args:
        jm_pairs: List of judge-meeting pairs
        rooms: List of Room objects
    
    Returns:
        Dict[int, int]: A dictionary mapping each room's ID to their calculated capacity.
    """
    # Group case_judge pairs by their room requirements
    requirement_groups = {}
    for jm_pair in jm_pairs:
        # Combine requirements from both case and judge
        combined_req = frozenset(
            list(jm_pair.meeting.case.room_requirements) + 
            list(jm_pair.judge.room_requirements)
        )
        if combined_req not in requirement_groups:
            requirement_groups[combined_req] = []
        requirement_groups[combined_req].append(jm_pair)
    
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
                compatible = (case_room_compatible(sample_pair.get_meeting().case, room) and 
                            judge_room_compatible(sample_pair.get_judge(), room))
            else:
                compatible = False

            competing_rooms = sum(1 for r in rooms if 
                                case_room_compatible(sample_pair.get_meeting().case, r) and 
                                judge_room_compatible(sample_pair.get_judge(), r))
            
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
    
    # Track fractional assignments by requirement group
    group_fractional_pairs = {}
    for req_group, count in group_counts.items():
        # Calculate how many pairs of this type were assigned as integers
        # Also track the actual fractional parts to avoid floating point errors
        total_fractional_parts = 0.0
        integer_assigned = 0
        
        for r in rooms:
            weight_contribution = room_weights[r.room_id][req_group] * count
            int_contribution = int(weight_contribution)
            integer_assigned += int_contribution
            # Track the actual fractional part
            total_fractional_parts += (weight_contribution - int_contribution)
        
        # Calculate the actual remaining count
        # This ensures we assign exactly the right number, avoiding floating point issues
        actual_remaining = count - integer_assigned
        if actual_remaining > 0:
            group_fractional_pairs[req_group] = actual_remaining
    
    # Track actual remaining capacity for each room
    room_remaining_capacity = {}
    for room in rooms:
        room_remaining_capacity[room.room_id] = float_capacities[room.room_id] - int_capacities[room.room_id]
    
    # Distribute remaining pairs by requirement group
    for req_group, remaining_count in group_fractional_pairs.items():
        # Get sample pair to check compatibility
        sample_pair = requirement_groups[req_group][0]
        
        # Get eligible rooms for this requirement group
        eligible_rooms = []
        for room in rooms:
            # Check if room can handle this requirement group
            if room_weights[room.room_id][req_group] > 0:
                # Calculate the fractional part FOR THIS SPECIFIC GROUP
                # Not the total fractional capacity of the room
                group_float_contribution = room_weights[room.room_id][req_group] * group_counts[req_group]
                group_int_contribution = int(group_float_contribution)
                group_fractional_part = group_float_contribution - group_int_contribution
                
                # Only include rooms with fractional remainder for this group
                # AND that still have remaining capacity (with small epsilon for floating point)
                if group_fractional_part > 0.01 and room_remaining_capacity[room.room_id] > 0.01:
                    eligible_rooms.append({
                        'room_id': room.room_id,
                        'current_capacity': int_capacities[room.room_id],
                        'remainder': min(group_fractional_part, room_remaining_capacity[room.room_id]),
                        'weight_for_group': room_weights[room.room_id][req_group]
                    })
        
        # Sort eligible rooms by current capacity (ascending), then remainder (descending)
        eligible_rooms.sort(key=lambda x: (x['current_capacity'], -x['remainder']))
        
        # Assign the remaining pairs of this type to eligible rooms
        assigned = 0
        for eligible_room in eligible_rooms:
            if assigned < remaining_count and room_remaining_capacity[eligible_room['room_id']] > 0.01:
                int_capacities[eligible_room['room_id']] += 1
                room_remaining_capacity[eligible_room['room_id']] -= 1.0
                assigned += 1
    
    # Safety check - ensure all pairs are assigned
    total_pairs = len(jm_pairs)
    total_assigned = sum(int_capacities.values())
    
    # Check if we need to adjust for overcounting
    if total_assigned > total_pairs:
        # We've overcounted - need to remove some assignments
        excess = total_assigned - total_pairs
        
        # Remove excess from rooms with highest capacity
        rooms_by_capacity = sorted(rooms, key=lambda r: int_capacities[r.room_id], reverse=True)
        for room in rooms_by_capacity:
            if excess > 0 and int_capacities[room.room_id] > 0:
                remove = min(excess, int_capacities[room.room_id])
                int_capacities[room.room_id] -= remove
                excess -= remove
        
        total_assigned = sum(int_capacities.values())
    
    if total_assigned != total_pairs:
        print(f"Warning: Room capacity calculation did not distribute all pairs. " +
              f"Assigned: {total_assigned}, Total: {total_pairs}")
        
        # Find room with highest original float capacity and add the difference
        if rooms:
            max_room = max(rooms, key=lambda r: float_capacities[r.room_id])
            difference = total_pairs - total_assigned
            int_capacities[max_room.room_id] += difference
    
    return int_capacities