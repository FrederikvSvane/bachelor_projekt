from src.base_model.schedule import Schedule
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.meeting import Meeting
from src.local_search.move import Move, do_move, undo_move
from src.local_search.move_generator import generate_specific_delete_move, generate_specific_insert_move
from src.local_search.rules_engine import calculate_delta_score
import random
from enum import Enum
from typing import Optional, Union, Tuple

class RRStrategy(Enum):
    """Enum for Ruin and Recreate strategy."""
    RANDOM_MEETINGS = "random meetings"
    RANDOM_JUDGE = "random judge"
    SPECIFIC_JUDGE = "specific judge"
    RANDOM_ROOM = "random room"
    SPECIFIC_ROOM = "specific room"
    RANDOM_DAY = "random day"
    SPECIFIC_DAY = "specific day"
    LONGEST_SCHEDULE_JUDGE = "longest schedule judge"

def apply_ruin_and_recreate(schedule: Schedule, 
                           compatible_judges_dict: dict[int, list[Judge]], 
                           compatible_rooms_dict: dict[int, list[Room]], 
                           strategy: RRStrategy,
                           specific_resource: Optional[Union[Judge, Room, int]] = None, 
                           percentage: int = 50) -> Tuple[bool, int]:
    """Apply ruin and recreate with a given strategy.
    
    Args:
        schedule: The schedule to modify
        compatible_judges_dict: Dictionary of compatible judges for each meeting
        compatible_rooms_dict: Dictionary of compatible rooms for each meeting
        strategy: Strategy to use for ruin and recreate
        specific_resource: Specific judge, room, or day to use (for specific strategies)
        percentage: Percentage of meetings to remove

    Returns:
        Tuple containing a boolean indicating success and the number of meetings inserted
    """
    
    # Apply chosen ruin strategy
    num_removed = 0
    
    if strategy == RRStrategy.RANDOM_MEETINGS:
        num_removed = _random_ruin(schedule, percentage)
    
    elif strategy == RRStrategy.RANDOM_JUDGE:
        num_removed = _related_ruin(schedule, 'judge', None, percentage)
    
    elif strategy == RRStrategy.SPECIFIC_JUDGE:
        if specific_resource is None or not isinstance(specific_resource, Judge):
            raise ValueError("Specific judge must be provided for SPECIFIC_JUDGE strategy")
        num_removed = _related_ruin(schedule, 'judge', specific_resource, percentage)
    
    elif strategy == RRStrategy.RANDOM_ROOM:
        num_removed = _related_ruin(schedule, 'room', None, percentage)
    
    elif strategy == RRStrategy.SPECIFIC_ROOM:
        if specific_resource is None or not isinstance(specific_resource, Room):
            raise ValueError("Specific room must be provided for SPECIFIC_ROOM strategy")
        num_removed = _related_ruin(schedule, 'room', specific_resource, percentage)
    
    elif strategy == RRStrategy.RANDOM_DAY:
        num_removed = _related_ruin(schedule, 'day', None, percentage)
    
    elif strategy == RRStrategy.SPECIFIC_DAY:
        if specific_resource is None or not isinstance(specific_resource, int):
            raise ValueError("Specific day (int) must be provided for SPECIFIC_DAY strategy")
        num_removed = _related_ruin(schedule, 'day', specific_resource, percentage)
    
    elif strategy == RRStrategy.LONGEST_SCHEDULE_JUDGE:
        longest_schedule_judge = _find_judge_with_longest_schedule(schedule)
        num_removed = _related_ruin(schedule, 'judge', longest_schedule_judge, percentage)

    # Stop if no meetings were removed
    if num_removed == 0:
        return False, 0
    
    # Apply recreate strategy
    num_inserted = _greedy_insert(schedule, compatible_judges_dict, compatible_rooms_dict)
    
    # Return success status and metrics
    return (num_inserted > 0), num_inserted

def _find_judge_with_longest_schedule(schedule: Schedule) -> Judge:
    # Start from the last day and work backwards
    for day in range(schedule.work_days, 0, -1):
        if day not in schedule.appointments_by_day_and_timeslot:
            continue
            
        # Start from the last timeslot and work backwards
        for timeslot in range(schedule.timeslots_per_work_day, 0, -1):
            if timeslot not in schedule.appointments_by_day_and_timeslot[day]:
                continue
                
            # If there are appointments in this timeslot, return the judge of the first one
            appointments = schedule.appointments_by_day_and_timeslot[day][timeslot]
            if appointments:
                return appointments[0].judge
    
    # If no appointments found, return a random judge
    if schedule.get_all_judges():
        return random.choice(schedule.get_all_judges())
    else:
        raise ValueError("No judges available in the schedule")


def _random_ruin(schedule: Schedule, percentage: int) -> int:
    """Remove a random percentage of meetings from the schedule."""
    meetings = schedule.get_all_planned_meetings()
    if not meetings:
        return 0
        
    num_to_remove = max(1, int(len(meetings) * percentage / 100))
    meetings_to_remove = random.sample(meetings, min(num_to_remove, len(meetings)))
    
    for meeting in meetings_to_remove:
        move = generate_specific_delete_move(schedule, meeting.meeting_id)
        do_move(move, schedule)
    
    return len(meetings_to_remove)


def _related_ruin(schedule: Schedule, resource_type: str, 
                 specific_resource: Optional[Union[Judge, Room, int]] = None, 
                 percentage: int = 50) -> int:
    """
    Remove meetings related by judge, room, or time.

    Args:
        schedule: The schedule to modify
        resource_type: Type of resource ('judge', 'room', or 'day')
        specific_resource: Specific judge, room, or day (if None, a random one is chosen)
        percentage: The percentage of related meetings to remove

    Returns:
        Number of meetings removed
    """
    all_meetings = schedule.get_all_meetings()
    if not all_meetings:
        return 0
        
    related_meetings = []
    
    if resource_type == 'judge':
        if specific_resource is None:
            # Select a random judge
            judges = schedule.get_all_judges()
            if not judges:
                return 0
            target_judge = random.choice(judges)
        else:
            # Use the specific judge
            target_judge = specific_resource
            
        # Remove meetings with this judge
        related_meetings = [m for m in all_meetings if m.judge and m.judge.judge_id == target_judge.judge_id]
        
    elif resource_type == 'room':
        if specific_resource is None:
            # Select a random room
            rooms = schedule.get_all_rooms()
            if not rooms:
                return 0
            target_room = random.choice(rooms)
        else:
            # Use the specific room
            target_room = specific_resource
            
        # Remove meetings with this room
        related_meetings = [m for m in all_meetings if m.room and m.room.room_id == target_room.room_id]
        
    elif resource_type == 'day':
        # Get all used days
        days_with_meetings = set(app.day for app in schedule.iter_appointments())
        if not days_with_meetings:
            return 0
            
        if specific_resource is None:
            # Select a random day
            target_day = random.choice(list(days_with_meetings))
        else:
            # Use the specific day
            target_day = specific_resource
            
        # Find meetings on this day
        related_meetings = []
        for meeting in all_meetings:
            for app in schedule.iter_appointments():
                if app.meeting.meeting_id == meeting.meeting_id and app.day == target_day:
                    related_meetings.append(meeting)
                    break
    
    if not related_meetings:
        return 0
        
    # Only remove up to the percentage
    num_to_remove = max(1, int(len(related_meetings) * percentage / 100))
    to_remove = random.sample(related_meetings, min(num_to_remove, len(related_meetings)))
    
    for meeting in to_remove:
        move = generate_specific_delete_move(schedule, meeting.meeting_id)
        do_move(move, schedule)
    
    return len(to_remove)


def _greedy_insert(schedule: Schedule, compatible_judges_dict, compatible_rooms_dict) -> int:
    """
    Insert unplanned meetings greedily (best insertion point for each).
    
    Returns:
        Number of meetings successfully inserted
    """
    unplanned = schedule.get_all_unplanned_meetings()
    if not unplanned:
        return 0
        
    unplanned = unplanned.copy()
    num_inserted = 0
    
    for meeting in unplanned:
        best_delta = float('inf')
        best_position = None
        best_judge = None
        best_room = None
        
        # Get compatible judges and rooms
        compatible_judges = compatible_judges_dict.get(meeting.case.case_id, [])
        compatible_rooms = compatible_rooms_dict.get(meeting.case.case_id, [])
        
        if not compatible_judges or not compatible_rooms:
            continue  # Skip this meeting if no compatible resources
        
        # Try each judge/room combination
        for judge in compatible_judges:
            for room in compatible_rooms:
                # Try each day and start time - STARTING FROM THE TOP AND WORKING DOWN
                for day in range(1, schedule.work_days + 1):
                    meeting_duration = (meeting.meeting_duration // schedule.granularity) + (1 if meeting.meeting_duration % schedule.granularity > 0 else 0)
                    max_start = schedule.timeslots_per_work_day - meeting_duration + 1
                    
                    for start_time in range(1, max_start + 1):
                        # Create a temporary insertion move
                        temp_move = generate_specific_insert_move(
                            schedule=schedule,
                            meeting=meeting,
                            judge=judge,
                            room=room,
                            day=day,
                            start_timeslot=start_time
                        )
                        
                        # Assign to meeting for scoring
                        meeting.judge = judge
                        meeting.room = room
                        
                        # Calculate score if inserted here
                        delta = calculate_delta_score(schedule, temp_move)

                        if delta < best_delta:
                            best_delta = delta
                            best_position = (day, start_time)
                            best_judge = judge
                            best_room = room
        
        # Insert at best position if found
        if best_position:
            # Create and apply insertion move
            insertion_move = generate_specific_insert_move(
                schedule=schedule,
                meeting=meeting,
                judge=best_judge,
                room=best_room,
                day=best_position[0],
                start_timeslot=best_position[1]
            )
            
            do_move(insertion_move, schedule)
            num_inserted += 1
    
    return num_inserted