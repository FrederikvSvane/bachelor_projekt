from src.base_model.schedule import Schedule
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.meeting import Meeting
from src.base_model.compatibility_checks import initialize_compatibility_matricies
from src.local_search.move import Move, do_move, undo_move
from src.local_search.move_generator import generate_specific_delete_move, generate_specific_insert_move
from src.local_search.rules_engine import calculate_delta_score, calculate_full_score, _initialize_constraint_weights
import random
import multiprocessing
from typing import List, Dict, Tuple
from concurrent.futures import ProcessPoolExecutor
import time

random.seed(13062025)  # Set seed for reproducibility

def apply_ruin_and_recreate(schedule: Schedule, 
                            compatible_judges_dict: dict[int, list[Judge]], 
                            compatible_rooms_dict: dict[int, list[Room]],
                            percentage: float = 0.1, #% of all meetings
                            in_parallel: bool = True,
                            log_file=None) -> Tuple[bool, int]:  # Changed to accept file object
    """Apply violation-based ruin and regret-based recreate.
    
    Args:
        schedule: The schedule to modify
        compatible_judges_dict: Dictionary of compatible judges for each meeting
        compatible_rooms_dict: Dictionary of compatible rooms for each meeting
        percentage: Percentage of meetings to remove based on violations
        parallel: Whether to use parallel processing
        log_file: Open file object for logging (not a string path)

    Returns:
        Tuple containing a boolean indicating success and the number of meetings inserted
    """
    # Define local log function that captures log_file through closure
    def log_output(message):
        print(message)  # Uncomment if you want console output too
        if log_file:
            log_file.write(message + "\n")
            log_file.flush()  # Ensure data is written immediately
    
    start_time = time.time()

    # Ruin phase - remove meetings with highest violations
    removed_meetings = _violation_based_ruin(schedule, compatible_judges_dict, compatible_rooms_dict, percentage, in_parallel, log_output)
    
    # Stop if no meetings were removed
    if not removed_meetings:
        return False, 0
    
    ruin_time = time.time() - start_time
    log_output(f"Ruined {len(removed_meetings)} meetings in {ruin_time:.2f} seconds")
    
    # Recreate phase - use regret-based insertion
    recreate_start = time.time()
    num_inserted = _regret_based_insert(schedule, compatible_judges_dict, compatible_rooms_dict, removed_meetings, in_parallel, log_output)
    recreate_time = time.time() - recreate_start
    
    log_output(f"Recreated {num_inserted} meetings in {recreate_time:.2f} seconds")
    log_output(f"Total R&R time: {time.time() - start_time:.2f} seconds")
    
    # Return success status and metrics
    return (num_inserted > 0), num_inserted

def _calculate_meeting_violations_parallel(args) -> Tuple[Meeting, float]:
    """Helper function for parallel violation calculation.
    
    Returns:
        Tuple containing the meeting and its delta score
    """
    schedule, meeting = args    
    
    # Create a delete move for the meeting
    delete_move = generate_specific_delete_move(schedule, meeting.meeting_id)
    
    # Calculate the delta score (negative delta means removing improves score)
    delta = calculate_delta_score(schedule, delete_move)
    
    # Return the meeting and improvement (negative value = higher violations)
    return meeting, delta


def _worker_initializer(init_schedule): #NOTE We do this because spawning a subprocess with concurrent.futures.ProcessPoolExecutor initializes a new process with its own Python interpreter and global variables, which are not initialized
    initialize_compatibility_matricies(schedule=init_schedule) 
    _initialize_constraint_weights(schedule=init_schedule) 
    #TODO this could be done better, using shared_memory from multiprocessing and pickle. But we do this because it works and time is money $$$

def _violation_based_ruin(schedule: Schedule, compatible_judges_dict: dict[int, list[Judge]], compatible_rooms_dict: dict[int, list[Room]], percentage: float, in_parallel: bool, log_output) -> List[Dict]:
    """
    Remove meetings and store their removal deltas for insertion strategy decision.
    """
    planned_meetings: list[Meeting] = schedule.get_all_planned_meetings()
    if not planned_meetings:
        return []
    
    log_output(f"Calculating violations for {len(planned_meetings)} meetings...")
    start_time = time.time()
    
    # Calculate violations for each meeting
    meeting_violations = []
    
    if in_parallel and len(planned_meetings) > 10:
        args_list = [(schedule, meeting) for meeting in planned_meetings]
        with ProcessPoolExecutor(initializer=_worker_initializer, initargs=(schedule,)) as executor:
            try:
                results = list(executor.map(_calculate_meeting_violations_parallel, args_list, timeout=120))
                meeting_violations: List[Tuple[Meeting, float]] = results
            except Exception as e:
                log_output(f"Error during parallel violation calculation: {e}")    
    else:
        for meeting in planned_meetings:
            violation_score = _calculate_meeting_violations_parallel((schedule, meeting))
            meeting_violations.append(violation_score)
    
    log_output(f"Violation calculation took {time.time() - start_time:.2f} seconds")
    
    # Sort by violation score (most violating first - lowest/most negative delta)
    meeting_violations.sort(key=lambda x: x[1])
    
    # Determine number of meetings to remove
    num_to_remove = max(1, int(len(meeting_violations) * percentage))
    meetings_to_remove = meeting_violations[:num_to_remove]
    
    log_output(f"Removing {len(meetings_to_remove)} meetings with deltas: {[(pair[0].meeting_id, pair[1]) for pair in meetings_to_remove]}")
    
    # Remove the meetings and store removal info including delta
    removed_meetings = []
    for meeting, removal_delta in meetings_to_remove:
        # Store the meeting information before removal INCLUDING the removal delta
        removed_meeting_info = {
            'meeting': meeting,
            'judge': meeting.judge,
            'room': meeting.room,
            'original_day': None,  # You'd need to track this from the schedule
            'original_timeslot': None,  # You'd need to track this from the schedule  
            'removal_delta': removal_delta  # KEY: Store the removal delta!
        }
        
        # Find original position before removing
        for day, timeslots in schedule.appointments_by_day_and_timeslot.items():
            for timeslot, appointments in timeslots.items():
                for appointment in appointments:
                    if appointment.meeting.meeting_id == meeting.meeting_id:
                        removed_meeting_info['original_day'] = day
                        removed_meeting_info['original_timeslot'] = timeslot
                        break
                if removed_meeting_info['original_day']: break
            if removed_meeting_info['original_day']: break
        
        removed_meetings.append(removed_meeting_info)
        
        # Create and apply delete move
        move = generate_specific_delete_move(schedule, meeting.meeting_id)
        do_move(move, schedule)
    
    return removed_meetings

def _is_position_available(schedule: Schedule, meeting, judge, room, day, start_timeslot) -> bool:
    """
    Check if a position is available for insertion without causing double booking.
    
    Args:
        schedule: Current schedule
        meeting: Meeting to insert
        judge: Judge to assign
        room: Room to assign
        day: Day to insert
        start_timeslot: Starting timeslot
        
    Returns:
        True if position is available, False otherwise
    """
    # Calculate meeting duration in timeslots
    meeting_duration = (meeting.meeting_duration // schedule.granularity) + (1 if meeting.meeting_duration % schedule.granularity > 0 else 0)
    
    # Check each timeslot needed by the meeting
    for offset in range(meeting_duration):
        current_timeslot = start_timeslot + offset
        
        # Handle day spillover
        current_day = day
        if current_timeslot > schedule.timeslots_per_work_day:
            current_day += (current_timeslot - 1) // schedule.timeslots_per_work_day
            current_timeslot = ((current_timeslot - 1) % schedule.timeslots_per_work_day) + 1
            
        # If we go beyond allowed days, position isn't available
        if current_day > schedule.work_days:
            return False
        
        # Check if the judge or room is already booked
        if current_day in schedule.appointments_by_day_and_timeslot and current_timeslot in schedule.appointments_by_day_and_timeslot[current_day]:
            for appointment in schedule.appointments_by_day_and_timeslot[current_day][current_timeslot]:
                if appointment.judge.judge_id == judge.judge_id:
                    return False
                if appointment.room.room_id == room.room_id:
                    return False
    
    return True

def _calculate_insertion_score_parallel(args):
    """Helper function for parallel insertion score calculation."""
    schedule, meeting, judge, room, day, start_timeslot = args
    
    # Create a temporary insertion move
    temp_move = generate_specific_insert_move(
        schedule=schedule,
        meeting=meeting,
        judge=judge,
        room=room,
        day=day,
        start_timeslot=start_timeslot
    )
    
    # Temporarily assign judge and room for scoring
    original_judge = meeting.judge
    original_room = meeting.room
    meeting.judge = judge
    meeting.room = room
    
    # Calculate score
    delta = calculate_delta_score(schedule, temp_move)
    
    # Reset judge and room
    meeting.judge = original_judge
    meeting.room = original_room
    
    return (delta, day, start_timeslot, judge, room)


def _regret_based_insert(schedule: Schedule, compatible_judges_dict, compatible_rooms_dict,
                         removed_meetings, parallel: bool, log_output) -> int:
    """
    Insert meetings using removal delta to decide strategy:
    - If removal_delta < 0: meeting was violating, use regret-based with pre-computation
    - If removal_delta >= 0: meeting was good, try original position then simple greedy
    """
    if not removed_meetings:
        return 0

    log_output(f"Starting delta-based insertion for {len(removed_meetings)} meetings")

    # Sort meetings by duration (longest first)
    removed_meetings.sort(key=lambda x: x['meeting'].meeting_duration, reverse=True)

    # STEP 1: Pre-compute positions and regret for violating meetings
    violating_meeting_evaluations = []  # (removed_info, regret, sorted_positions)
    positions_evaluated = 0
    
    for removed_info in removed_meetings:
        if removed_info['removal_delta'] < 0:  # Only pre-compute for violating meetings
            meeting = removed_info['meeting']
            compatible_judges = compatible_judges_dict.get(meeting.case.case_id, [])
            compatible_rooms = compatible_rooms_dict.get(meeting.case.case_id, [])

            if not compatible_judges or not compatible_rooms:
                log_output(f"Warning: No compatible judges or rooms for meeting {meeting.meeting_id}, skipping.")
                continue

            available_positions_args = []
            meeting_duration_slots = meeting.meeting_duration // schedule.granularity

            # Build all possible positions for this violating meeting
            for judge in compatible_judges:
                for room in compatible_rooms:
                    for day in range(1, schedule.work_days + 1):
                        max_start = schedule.timeslots_per_work_day - meeting_duration_slots + 1
                        if max_start < 1: continue

                        for start_time in range(1, max_start + 1, 2):
                            if _is_position_available(schedule, meeting, judge, room, day, start_time):
                                available_positions_args.append((schedule, meeting, judge, room, day, start_time))

            if not available_positions_args:
                log_output(f"Warning: No initially available positions found for violating meeting {meeting.meeting_id}")
                continue

            positions_evaluated += len(available_positions_args)

            # Calculate scores for all positions
            position_scores = []
            if parallel and len(available_positions_args) > 10:
                with ProcessPoolExecutor(initializer=_worker_initializer, initargs=(schedule,)) as executor:
                    results = list(executor.map(_calculate_insertion_score_parallel, available_positions_args))
                    position_scores.extend(results)
            else:
                for args in available_positions_args:
                    score_result = _calculate_insertion_score_parallel(args)
                    position_scores.append(score_result)

            position_scores.sort(key=lambda x: x[0])  # Sort by delta score

            # Calculate regret
            regret = 0.0
            if len(position_scores) >= 2:
                best_delta = position_scores[0][0]
                second_best_delta = position_scores[1][0]
                regret = second_best_delta - best_delta
            elif len(position_scores) == 1:
                regret = float('inf')

            violating_meeting_evaluations.append((removed_info, regret, position_scores))

    log_output(f"Pre-computed {positions_evaluated} positions for {len(violating_meeting_evaluations)} violating meetings")

    # Sort violating meetings by regret (highest first)
    violating_meeting_evaluations.sort(key=lambda x: x[1], reverse=True)

    num_inserted = 0

    # STEP 2: Insert violating meetings in regret order
    for removed_info, regret, sorted_positions in violating_meeting_evaluations:
        meeting = removed_info['meeting']
        log_output(f"  Meeting {meeting.meeting_id}: Was violating (delta={removed_info['removal_delta']:.2f}, regret={regret:.2f}) - regret-based insertion")

        best_position = None
        # Try positions from best to worst until we find one that's currently available
        for position_info in sorted_positions:
            delta, day, start_timeslot, judge, room = position_info
            
            if _is_position_available(schedule, meeting, judge, room, day, start_timeslot):
                best_position = (judge, room, day, start_timeslot)
                log_output(f"    Best available position: Day {day}, Slot {start_timeslot}, Delta: {delta:.2f}")
                break

        if best_position:
            judge, room, day, start_timeslot = best_position
            insertion_move = generate_specific_insert_move(
                schedule=schedule, meeting=meeting, judge=judge, room=room, day=day, start_timeslot=start_timeslot
            )
            do_move(insertion_move, schedule)
            num_inserted += 1
            log_output(f"  ✓ Inserted violating meeting {meeting.meeting_id}")
        else:
            log_output(f"  ✗ Could not find position for violating meeting {meeting.meeting_id}")

    # STEP 3: Insert good meetings (simple approach)
    for removed_info in removed_meetings:
        if removed_info['removal_delta'] >= 0:  # Good meetings
            meeting = removed_info['meeting']
            removal_delta = removed_info['removal_delta']
            original_day = removed_info['original_day']
            original_timeslot = removed_info['original_timeslot']
            
            compatible_judges = compatible_judges_dict.get(meeting.case.case_id, [])
            compatible_rooms = compatible_rooms_dict.get(meeting.case.case_id, [])

            if not compatible_judges or not compatible_rooms:
                log_output(f"Warning: No compatible judges or rooms for meeting {meeting.meeting_id}, skipping.")
                continue

            meeting_duration_slots = meeting.meeting_duration // schedule.granularity
            
            log_output(f"  Meeting {meeting.meeting_id}: Was good (delta={removal_delta:.2f}) - trying original/greedy")
            
            best_position = None
            
            # First try original position if available
            if (original_day and original_timeslot and 
                removed_info['judge'] in compatible_judges and 
                removed_info['room'] in compatible_rooms):
                
                if _is_position_available(schedule, meeting, removed_info['judge'], 
                                        removed_info['room'], original_day, original_timeslot):
                    best_position = (removed_info['judge'], removed_info['room'], 
                                   original_day, original_timeslot)
                    log_output(f"    Restored to original position: Day {original_day}, Slot {original_timeslot}")
            
            # If original position not available, do simple greedy search
            if not best_position:
                for judge in compatible_judges:
                    for room in compatible_rooms:
                        for day in range(1, schedule.work_days + 1):
                            max_start = schedule.timeslots_per_work_day - meeting_duration_slots + 1
                            if max_start < 1: continue
                            
                            for start_time in range(1, max_start + 1):
                                if _is_position_available(schedule, meeting, judge, room, day, start_time):
                                    best_position = (judge, room, day, start_time)
                                    break
                            if best_position: break
                        if best_position: break
                    if best_position: break
                
                if best_position:
                    log_output(f"    Greedy insert: Day {best_position[2]}, Slot {best_position[3]}")

            # Insert the meeting if we found a position
            if best_position:
                judge, room, day, start_timeslot = best_position
                
                insertion_move = generate_specific_insert_move(
                    schedule=schedule,
                    meeting=meeting,
                    judge=judge,
                    room=room,
                    day=day,
                    start_timeslot=start_timeslot
                )
                
                do_move(insertion_move, schedule)
                num_inserted += 1
                log_output(f"  ✓ Inserted good meeting {meeting.meeting_id}")
            else:
                log_output(f"  ✗ Could not find position for good meeting {meeting.meeting_id}")

    return num_inserted