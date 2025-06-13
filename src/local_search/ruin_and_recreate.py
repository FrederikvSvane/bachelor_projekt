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
    # convert percentage to int
    percentage = int(percentage * 100)
    """
    Remove a percentage of meetings with the highest constraint violations.
    
    Args:
        schedule: Schedule to modify
        percentage: Percentage of meetings to remove
        parallel: Whether to use parallel processing for calculating violations
        log_output: Logging function
        
    Returns:
        List of removed meeting info dictionaries
    """
    planned_meetings: list[Meeting] = schedule.get_all_planned_meetings()
    if not planned_meetings:
        return []
    
    log_output(f"Calculating violations for {len(planned_meetings)} meetings...")
    start_time = time.time()
    
    # Calculate violations for each meeting
    meeting_violations = []
    
    if in_parallel and len(planned_meetings) > 10:  # Only parallelize for significant workloads
        # Prepare arguments for parallel execution
        args_list = [(schedule, meeting) for meeting in planned_meetings]
        
        # Use ProcessPoolExecutor for parallel execution
        with ProcessPoolExecutor(initializer=_worker_initializer, initargs=(schedule,)) as executor:
            try:
                results = list(executor.map(_calculate_meeting_violations_parallel, args_list, timeout=120))
                meeting_violations: List[Tuple[Meeting, int]] = results # List of tuples (meeting, delta)
            except TimeoutError:
                log_output("Error: Violation calculation timed out. Proceeding with available results.")
            except Exception as e:
                log_output(f"Error during parallel violation calculation: {e}")    
    else:
        # Sequential calculation
        for meeting in planned_meetings:
            violation_score = _calculate_meeting_violations_parallel((schedule, meeting))
            meeting_violations.append(violation_score)
    
    log_output(f"Violation calculation took {time.time() - start_time:.2f} seconds")
    
    # Sort by violation score (most violating first - lowest/most negative delta)
    meeting_violations.sort(key=lambda x: x[1])
    
    # Determine number of meetings to remove
    num_to_remove = max(1, int(len(planned_meetings) * percentage / 100))
    meetings_to_remove = [meeting for meeting, _ in meeting_violations[:num_to_remove]]
    
    log_output(f"Top {num_to_remove} meeting violations with deltas: {[(pair[0].meeting_id, pair[1]) for pair in meeting_violations[:num_to_remove]]}")
    log_output(f"Removing {len(meetings_to_remove)} most violating meetings")
    
    # Remove the meetings
    removed_meetings = []
    for meeting in meetings_to_remove:
        # Store the meeting information before removal
        removed_meeting_info = {
            'meeting': meeting,
            'judge': meeting.judge,
            'room': meeting.room
        }
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
    Insert meetings using regret-based insertion, checking availability dynamically.
    Specifically, 2-regret insert with a maintained list of best positions dynamic availability check. 
    
    Args:
        schedule: The schedule to modify
        compatible_judges_dict: Dictionary of compatible judges for each meeting
        compatible_rooms_dict: Dictionary of compatible rooms for each meeting
        removed_meetings: List of dicts with meeting info to reinsert
        parallel: Whether to use parallel processing for calculating scores
        log_output: Logging function

    Returns:
        Number of meetings successfully inserted
    """
    if not removed_meetings:
        return 0

    log_output(f"Starting regret-based insertion for {len(removed_meetings)} meetings")

    # Sort meetings by duration (longest first)
    removed_meetings.sort(key=lambda x: x['meeting'].meeting_duration, reverse=True)

    # Store all evaluated positions and regrets for each meeting
    meeting_evaluations = [] # List to store tuples: (meeting, regret, sorted_positions_list)
                              # sorted_positions_list contains tuples: (delta, day, start_timeslot, judge, room)
    positions_evaluated = 0

    for removed_info in removed_meetings:
        meeting = removed_info['meeting']
        compatible_judges = compatible_judges_dict.get(meeting.case.case_id, []) # Use case_id if dict is keyed by case
        compatible_rooms = compatible_rooms_dict.get(meeting.case.case_id, [])   # Use case_id if dict is keyed by case

        if not compatible_judges or not compatible_rooms:
            log_output(f"Warning: No compatible judges or rooms for meeting {meeting.meeting_id}, skipping.")
            continue

        available_positions_args = []
        meeting_duration_slots = (meeting.meeting_duration // schedule.granularity) # + (1 if meeting.meeting_duration % schedule.granularity > 0 else 0) #NOTE this handles durations that are not multiples of granularity. But we should not need this if the input data is correct.

        for judge in compatible_judges:
            for room in compatible_rooms:
                for day in range(1, schedule.work_days + 1):
                    max_start = schedule.timeslots_per_work_day - meeting_duration_slots + 1
                    if max_start < 1: continue # Meeting too long for this day configuration. Shuouldn't happen, but just in case.

                    for start_time in range(1, max_start + 1, 2): # Step by 2 or 1 as desired
                        # Check initial availability (against schedule before insertions)
                        if _is_position_available(schedule, meeting, judge, room, day, start_time):
                            available_positions_args.append((schedule, meeting, judge, room, day, start_time))

        if not available_positions_args:
            log_output(f"Warning: No initially available positions found for meeting {meeting.meeting_id}, skipping.")
            continue

        positions_evaluated += len(available_positions_args)

        position_scores = [] # List of tuples: (delta, day, start_timeslot, judge, room)
        if parallel and len(available_positions_args) > 10:
            with ProcessPoolExecutor(initializer=_worker_initializer, initargs=(schedule,)) as executor:
                results = list(executor.map(_calculate_insertion_score_parallel, available_positions_args))
                position_scores.extend(results) # results are already (delta, day, start_timeslot, judge, room)
        else:
            for args in available_positions_args:
                 score_result = _calculate_insertion_score_parallel(args)
                 position_scores.append(score_result)

        position_scores.sort(key=lambda x: x[0]) # Sort by delta score #NOTE we dont use reverse=True, because we want the lowest delta first (negative delta = better score)

        regret = 0.0
        if len(position_scores) >= 2:
            best_delta = position_scores[0][0]
            second_best_delta = position_scores[1][0]
            regret = second_best_delta - best_delta
        elif len(position_scores) == 1:
            regret = float('inf') # Prioritize meetings with only one option (rare but possible)

        # Store the meeting, its regret, and its full sorted list of potential positions
        meeting_evaluations.append((meeting, regret, position_scores))

    log_output(f"Evaluated {positions_evaluated} initial positions for {len(meeting_evaluations)} meetings")

    meeting_evaluations.sort(key=lambda x: x[1], reverse=True) # Sort by regret (highest first)

    num_inserted = 0
    for meeting, regret, sorted_positions in meeting_evaluations:
        inserted_this_meeting = False
        log_output(f"Attempting insertion for meeting {meeting.meeting_id} (Regret: {regret:.2f})")

        # Iterate through the pre-calculated positions, starting with the best
        for position_info in sorted_positions:
            delta, day, start_timeslot, judge, room = position_info

            # Re-check availability against CURRENT schedule
            if _is_position_available(schedule, meeting, judge, room, day, start_timeslot):
                # Found the best *currently* available position from the initial list
                log_output(f"  Inserting meeting {meeting.meeting_id} at Day {day}, Slot {start_timeslot}, Judge {judge.judge_id}, Room {room.room_id}")

                insertion_move = generate_specific_insert_move(
                    schedule=schedule, 
                    meeting=meeting,
                    judge=judge,
                    room=room,
                    day=day,
                    start_timeslot=start_timeslot
                )

                # Execute the move, modifying the schedule
                do_move(insertion_move, schedule)
                num_inserted += 1
                inserted_this_meeting = True
                break # Stop searching for positions for this meeting

        if not inserted_this_meeting:
            log_output(f"  Warning: Could not find a currently available position for meeting {meeting.meeting_id} from its initial list. Leaving unplanned.")

    return num_inserted