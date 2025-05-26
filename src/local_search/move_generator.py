import random
from typing import Dict, List

from src.base_model.meeting import Meeting
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.schedule import Schedule
from src.local_search.move import Move, ContractingMove, do_move
from collections import deque
from src.local_search.rules_engine import calculate_delta_score
from src.base_model.compatibility_checks import calculate_compatible_judges, calculate_compatible_rooms
from src.local_search.rules_engine_helpers import populate_insert_move_appointments

random.seed(13062025)

def generate_single_random_move(
    schedule: Schedule,
    compatible_judges_dict: Dict[int, List[Judge]],
    compatible_rooms_dict: Dict[int, List[Room]],
    tabu_list: deque = None,
    current_score: int = None,
    best_score: int = None
) -> Move:
    """Generate a random valid move with inline tabu checking."""
    meetings = schedule.get_all_meetings()
    if not meetings:
        raise ValueError("No meetings found in the schedule.")
    
    chosen_meeting_id = random.choice(meetings).meeting_id
    chosen_appointments = sorted(
        schedule.get_appointment_chain(chosen_meeting_id),
        key=lambda app: (app.day, app.timeslot_in_day)
    )
    first_app = chosen_appointments[0]
    current_day = first_app.day
    current_start = first_app.timeslot_in_day
    
    move = Move(chosen_meeting_id, chosen_appointments)
    move.old_judge = first_app.judge
    move.old_room = first_app.room
    move.old_day = current_day
    move.old_start_timeslot = current_start
    
    def meets_aspiration(temp_move: Move) -> bool:
        if current_score is None or best_score is None:
            return False
        delta = calculate_delta_score(schedule, temp_move)
        return current_score + delta < best_score
    
    # Precompute some values
    meeting_length = len(chosen_appointments)
    max_start = schedule.timeslots_per_work_day - meeting_length + 1
    
    compatible_judges = compatible_judges_dict.get(chosen_meeting_id, [])
    compatible_rooms  = compatible_rooms_dict.get(chosen_meeting_id, [])
    
    # Build lists of valid alternatives
    valid_judges = []
    for j in compatible_judges:
        if j.judge_id == first_app.judge.judge_id:
            continue
        key = (chosen_meeting_id, 'judge', j.judge_id)
        if tabu_list is None or key not in tabu_list:
            valid_judges.append(j)
        else:
            temp = Move(chosen_meeting_id, chosen_appointments,
                        old_judge=first_app.judge, new_judge=j,
                        old_room=first_app.room,
                        old_day=current_day, old_start_timeslot=current_start)
            if meets_aspiration(temp):
                valid_judges.append(j)
    
    valid_rooms = []
    for r in compatible_rooms:
        if r.room_id == first_app.room.room_id:
            continue
        key = (chosen_meeting_id, 'room', r.room_id)
        if tabu_list is None or key not in tabu_list:
            valid_rooms.append(r)
        else:
            temp = Move(chosen_meeting_id, chosen_appointments,
                        old_judge=first_app.judge,
                        old_room=first_app.room, new_room=r,
                        old_day=current_day, old_start_timeslot=current_start)
            if meets_aspiration(temp):
                valid_rooms.append(r)
    
    valid_days = []
    for d in range(1, schedule.work_days + 1):
        if d == current_day:
            continue
        key = (chosen_meeting_id, 'position', d, current_start)
        if tabu_list is None or key not in tabu_list:
            valid_days.append(d)
        else:
            temp = Move(chosen_meeting_id, chosen_appointments,
                        old_judge=first_app.judge, old_room=first_app.room,
                        old_day=current_day, new_day=d,
                        old_start_timeslot=current_start)
            if meets_aspiration(temp):
                valid_days.append(d)
    
    valid_timeslots = []
    if meeting_length != 78:
        for t in range(1, max_start + 1):
            if t == current_start:
                continue
            key = (chosen_meeting_id, 'position', current_day, t)
            if tabu_list is None or key not in tabu_list:
                valid_timeslots.append(t)
            else:
                temp = Move(chosen_meeting_id, chosen_appointments,
                            old_judge=first_app.judge, old_room=first_app.room,
                            old_day=current_day, old_start_timeslot=current_start,
                            new_start_timeslot=t)
                if meets_aspiration(temp):
                    valid_timeslots.append(t)
    
    # Map move‐types to their valid options
    move_buckets = {
        "judge":   valid_judges,
        "room":    valid_rooms,
        "day":     valid_days,
        "timeslot": valid_timeslots
    }
    possible_moves = [m for m, opts in move_buckets.items() if opts]
    if not possible_moves:
        raise ValueError(f"No valid moves for meeting_length={meeting_length}")
    
    move_type = random.choice(possible_moves)
    
    # Assign the chosen alternative
    if move_type == "judge":
        move.new_judge = random.choice(valid_judges)
    elif move_type == "room":
        move.new_room = random.choice(valid_rooms)
    elif move_type == "day":
        move.new_day = random.choice(valid_days)
    elif move_type == "timeslot":
        move.new_start_timeslot = random.choice(valid_timeslots)
    
    return move



def generate_specific_delete_move(schedule: Schedule, meeting_id: int) -> Move:
    """
    Generate a delete move for a specific meeting ID.
    """
    if meeting_id is None:
        raise ValueError("Meeting ID cannot be None.")
    
    chosen_appointments = schedule.get_appointment_chain(meeting_id)
    
    if not chosen_appointments:
        raise ValueError(f"No appointments found for meeting ID {meeting_id}.")
    
    first_appointment = chosen_appointments[0]
    day = first_appointment.day
    start_timeslot = first_appointment.timeslot_in_day
    judge = first_appointment.judge
    room = first_appointment.room
    
    # print(f"Deleting meeting {meeting_id} with judge {judge.judge_id} in room {room.room_id}")
    
    move = Move(
        meeting_id=meeting_id, 
        appointments=chosen_appointments,
        old_judge=judge,
        old_room=room,
        old_day=day,
        old_start_timeslot=start_timeslot,
        is_delete_move=True
    )
    
    return move

def generate_random_delete_move(schedule: Schedule) -> Move:
    """
    Generate a delete move for a random meeting.
    """
    meetings = schedule.get_all_planned_meetings()
    
    if not meetings:
        raise ValueError("No meetings found in schedule.")
    
    meeting = random.choice(meetings)
    meeting_id = meeting.meeting_id
    chosen_appointments = schedule.get_appointment_chain(meeting_id)
    
    if not chosen_appointments:
        raise ValueError(f"No appointments found for meeting ID {meeting_id}.")
    
    first_appointment = chosen_appointments[0]
    day = first_appointment.day
    start_timeslot = first_appointment.timeslot_in_day
    judge = first_appointment.judge
    room = first_appointment.room
    
    # print(f"Deleting meeting {meeting_id} with judge {judge.judge_id} in room {room.room_id}")
    
    move = Move(
        meeting_id=meeting_id, 
        appointments=chosen_appointments,
        old_judge=judge,
        old_room=room,
        old_day=day,
        old_start_timeslot=start_timeslot,
        is_delete_move=True
    )
    return move

def generate_specific_insert_move(schedule: Schedule, meeting: Meeting, judge: Judge, room: Room, day: int, start_timeslot: int) -> Move:
    #NOTE the check below clashes with the schedule state during parallel subprocesses during ruin and recreate. So leaving it out for now.
    # if meeting not in schedule.get_all_unplanned_meetings():
    #     raise ValueError("Meeting not found in unplanned meetings for schedule. Will not generate insert move.")
    if judge is None or room is None or day is None or start_timeslot is None:
        raise ValueError("Judge, room, day, and start_timeslot cannot be None. Will not generate insert move.")

    move = Move(
        meeting_id=meeting.meeting_id,
        appointments=[],  # Will be populated in do_move
        old_judge=None,   # Not needed for insert
        new_judge=judge,
        old_room=None,    # Not needed for insert
        new_room=room,
        old_day=None,     # Not needed for insert
        new_day=day,
        old_start_timeslot=None,  # Not needed for insert
        new_start_timeslot=start_timeslot,
        is_delete_move=False,
        is_insert_move=True
    )
    
    return move

def generate_random_insert_move(schedule: Schedule) -> Move:
    """ 
    Generate an insert move for a random unplanned meeting.
    """
    
    unplanned_meetings = schedule.get_all_unplanned_meetings()
    
    if not unplanned_meetings:
        raise ValueError("No unplanned meetings found in schedule.")
    
    meeting = random.choice(unplanned_meetings)
    meeting_id = meeting.meeting_id
    
    compatible_judges_dict = calculate_compatible_judges(schedule.get_all_meetings(), schedule.get_all_judges())
    compatible_rooms_dict = calculate_compatible_rooms(schedule.get_all_meetings(), schedule.get_all_rooms())
    
    if meeting_id not in compatible_judges_dict or not compatible_judges_dict[meeting_id]:
        raise ValueError(f"No compatible judges found for meeting ID {meeting_id}.")
    if meeting_id not in compatible_rooms_dict or not compatible_rooms_dict[meeting_id]:
        raise ValueError(f"No compatible rooms found for meeting ID {meeting_id}.")
    
    judge = random.choice(compatible_judges_dict[meeting_id])
    room = random.choice(compatible_rooms_dict[meeting_id])
    
    # Randomly select a day and timeslot
    day = random.randint(1, schedule.work_days)
    required_timeslots = meeting.meeting_duration // schedule.granularity
    max_start_timeslot = schedule.timeslots_per_work_day - required_timeslots + 1
    
    if max_start_timeslot < 1:
        raise ValueError(f"Meeting {meeting_id} which requires {required_timeslots} timeslots is too long for a single day ({schedule.timeslots_per_work_day} slots).")
    
    start_timeslot = random.randint(1, max_start_timeslot)
    
    # print(f"Inserting meeting {meeting_id} with judge {judge.judge_id} in room {room.room_id}")
    
    move = Move(
        meeting_id=meeting_id,
        appointments=[],
        old_judge=None,  # Previously unplanned, so no old judge
        new_judge=judge,
        old_room=None,   # Likewise, no old room
        new_room=room,
        old_day=None,    # Likewise
        new_day=day,
        old_start_timeslot=None,  # Likewise
        new_start_timeslot=start_timeslot,
        is_insert_move=True
    )
    
    populate_insert_move_appointments(schedule, move)
    
    return move

def generate_compound_move(
    schedule: Schedule, 
    compatible_judges_dict: Dict[int, List[Judge]], 
    compatible_rooms_dict: Dict[int, List[Room]],
    p_j: float = 0.5, p_r: float = 0.5, 
    p_t: float = 0.5, p_d: float = 0.5,
    tabu_list: deque = None, current_score: int = None, 
    best_score: int = None
) -> Move:
    
    """Generate a compound move with inline tabu checking; fallback to single if <2 aspects."""
    if not schedule:
        raise ValueError("No schedule provided")
    chain_dict = schedule.appointment_chains
    if not chain_dict:
        raise ValueError("No appointments found in schedule")
    
    # Pick a random meeting
    chosen_meeting_id = random.choice(list(chain_dict.keys()))
    chosen_appointments = chain_dict[chosen_meeting_id]
    if not chosen_appointments:
        raise ValueError(f"No appointments for meeting {chosen_meeting_id}")
    
    first_app = chosen_appointments[0]
    old_judge = first_app.judge
    old_room  = first_app.room
    old_day   = first_app.day
    old_slot  = first_app.timeslot_in_day
    
    # Helper for aspiration
    def meets_aspiration(m: Move) -> bool:
        if current_score is None or best_score is None or tabu_list is None:
            return False
        if not check_if_move_is_tabu(m, tabu_list):
            return True
        return current_score + calculate_delta_score(schedule, m) < best_score
    
    # Build valid lists
    valid_judges = []
    for j in compatible_judges_dict.get(chosen_meeting_id, []):
        if j.judge_id == old_judge.judge_id: continue
        key = (chosen_meeting_id, 'judge', j.judge_id)
        m = Move(chosen_meeting_id, chosen_appointments,
                 old_judge=old_judge, new_judge=j,
                 old_room=old_room, old_day=old_day, old_start_timeslot=old_slot)
        if tabu_list is None or key not in tabu_list or meets_aspiration(m):
            valid_judges.append(j)
    valid_rooms = []
    for r in compatible_rooms_dict.get(chosen_meeting_id, []):
        if r.room_id == old_room.room_id: continue
        key = (chosen_meeting_id, 'room', r.room_id)
        m = Move(chosen_meeting_id, chosen_appointments,
                 old_judge=old_judge, old_room=old_room, new_room=r,
                 old_day=old_day, old_start_timeslot=old_slot)
        if tabu_list is None or key not in tabu_list or meets_aspiration(m):
            valid_rooms.append(r)
    valid_days = []
    for d in range(1, schedule.work_days + 1):
        if d == old_day: continue
        key = (chosen_meeting_id, 'position', d, old_slot)
        m = Move(chosen_meeting_id, chosen_appointments,
                 old_judge=old_judge, old_room=old_room,
                 old_day=old_day, new_day=d, old_start_timeslot=old_slot)
        if tabu_list is None or key not in tabu_list or meets_aspiration(m):
            valid_days.append(d)
    # timeslot aspect (skip 78‐slot meetings)
    meeting_length = len(chosen_appointments)
    valid_timeslots = []
    if meeting_length != 78:
        max_start = schedule.timeslots_per_work_day - meeting_length + 1
        for t in range(1, max_start + 1):
            if t == old_slot: continue
            key = (chosen_meeting_id, 'position', old_day, t)
            m = Move(chosen_meeting_id, chosen_appointments,
                     old_judge=old_judge, old_room=old_room,
                     old_day=old_day, old_start_timeslot=old_slot,
                     new_start_timeslot=t)
            if tabu_list is None or key not in tabu_list or meets_aspiration(m):
                valid_timeslots.append(t)
    
    # Collect aspects
    changeable_aspects = []
    if valid_judges:   changeable_aspects.append(("judge",   valid_judges,   p_j))
    if valid_rooms:    changeable_aspects.append(("room",    valid_rooms,    p_r))
    if valid_days:     changeable_aspects.append(("day",     valid_days,     p_d))
    if valid_timeslots:changeable_aspects.append(("timeslot",valid_timeslots,p_t))
    
    # Fallback if we don’t have at least 2 aspects
    if len(changeable_aspects) < 2:
        return generate_single_random_move(
            schedule, compatible_judges_dict, compatible_rooms_dict,
            tabu_list, current_score, best_score
        )
    
    # Now pick at least 2 aspects (by p_*, then fill to 2)
    selected = []
    for name, opts, prob in changeable_aspects:
        if random.random() < prob:
            selected.append((name, opts))
    # ensure two
    if len(selected) < 2:
        remaining = [ (n,o) for n,o,_ in changeable_aspects if n not in {s[0] for s in selected} ]
        random.shuffle(remaining)
        selected.extend(remaining[:2-len(selected)])
    
    # Build final Move
    move = Move(
        meeting_id=chosen_meeting_id,
        appointments=chosen_appointments,
        old_judge=old_judge,
        old_room=old_room,
        old_day=old_day,
        old_start_timeslot=old_slot
    )
    for name, opts in selected:
        if name == "judge":
            move.new_judge = random.choice(opts)
        elif name == "room":
            move.new_room = random.choice(opts)
        elif name == "day":
            move.new_day = random.choice(opts)
        elif name == "timeslot":
            move.new_start_timeslot = random.choice(opts)
    
    return move

def check_if_move_is_tabu(move: Move, tabu_list: deque) -> bool:
    meeting_id = move.meeting_id
    if move.new_judge:
        if (meeting_id, 'judge', move.new_judge.judge_id) in tabu_list: return True
    if move.new_room:
        if (meeting_id, 'room', move.new_room.room_id) in tabu_list: return True
    if move.new_day or move.new_start_timeslot:
        target_day = move.new_day if move.new_day is not None else move.old_day
        target_slot = move.new_start_timeslot if move.new_start_timeslot is not None else move.old_start_timeslot
        if (meeting_id, 'position', target_day, target_slot) in tabu_list: return True
    return False
# ---


def pick_meeting_for_move(schedule: Schedule):
    chain_dict = schedule.appointment_chains
    chosen_meeting_id = random.choice(list(chain_dict.keys()))
    
    chosen_appointments = sorted(chain_dict[chosen_meeting_id], key=lambda app: (app.day, app.timeslot_in_day))
    
    return (chosen_meeting_id, chosen_appointments) 

def generate_list_of_random_moves(schedule: Schedule,
                              compatible_judges_dict: Dict[int, List[Judge]],
                              compatible_rooms_dict: Dict[int, List[Room]],
                              tabu_list: deque, current_score: int, best_score: int):
    """
    Generates a list of valid, non-Tabu moves of a randomly selected type
    for a randomly selected meeting. Includes validity checks.
    """
    # 1. Pick Meeting
    (chosen_meeting_id, chosen_appointments) = pick_meeting_for_move(schedule)
    if chosen_meeting_id is None:
        return []

    first_appointment = chosen_appointments[0]
    old_judge = first_appointment.judge
    old_room = first_appointment.room
    old_day = first_appointment.day
    old_start_timeslot = first_appointment.timeslot_in_day
    meeting_length = len(chosen_appointments)

    # 2. Determine possible move types and select one randomly
    possible_types = []
    n_compatible_judges = len(compatible_judges_dict.get(chosen_meeting_id, []))
    n_compatible_rooms = len(compatible_rooms_dict.get(chosen_meeting_id, []))

    if n_compatible_judges > 1: possible_types.append("judge")
    if n_compatible_rooms > 1: possible_types.append("room")
    if schedule.work_days > 1: possible_types.append("day")

    max_start_timeslot_calc = schedule.timeslots_per_work_day - meeting_length + 1
    if max_start_timeslot_calc < 1: max_start_timeslot_calc = 1 # Ensure it's at least 1 if possible

    # Check if there is ANY valid starting timeslot different from the current one
    can_change_timeslot = False
    for t in range(1, max_start_timeslot_calc + 1):
        if t != old_start_timeslot:
            can_change_timeslot = True
            break
    if can_change_timeslot:
        possible_types.append("timeslot")

    if not possible_types:
        return []

    move_type = random.choice(possible_types)

    # 3. Generate list of valid, non-Tabu moves of the chosen type
    valid_moves: list[(Move, int)] = []

    # --- Judge Moves ---
    if move_type == "judge":
        if chosen_meeting_id in compatible_judges_dict:
            for judge in compatible_judges_dict[chosen_meeting_id]:
                if judge.judge_id == old_judge.judge_id: continue
                potential_move = Move(
                    meeting_id=chosen_meeting_id, appointments=chosen_appointments,
                    old_judge=old_judge, new_judge=judge, old_room=old_room,
                    old_day=old_day, old_start_timeslot=old_start_timeslot
                )
                is_tabu = check_if_move_is_tabu(potential_move, tabu_list)
                if not is_tabu:
                    valid_moves.append((potential_move, 0))
                else:
                    delta = calculate_delta_score(schedule, potential_move)
                    if current_score + delta < best_score:
                        valid_moves.append((potential_move, delta))

    # --- Room Moves ---
    elif move_type == "room":
        if chosen_meeting_id in compatible_rooms_dict:
            for room in compatible_rooms_dict[chosen_meeting_id]:
                if room.room_id == old_room.room_id: continue
                potential_move = Move(
                    meeting_id=chosen_meeting_id, appointments=chosen_appointments,
                    old_judge=old_judge, old_room=old_room, new_room=room,
                    old_day=old_day, old_start_timeslot=old_start_timeslot
                )
                is_tabu = check_if_move_is_tabu(potential_move, tabu_list)
                if not is_tabu:
                    valid_moves.append((potential_move, 0))
                else:
                    delta = calculate_delta_score(schedule, potential_move)
                    if current_score + delta < best_score:
                        valid_moves.append((potential_move, delta))

    # --- Day Moves ---
    elif move_type == "day":
        for day in range(1, schedule.work_days + 1):
            if day == old_day: continue

            potential_move = Move(
                meeting_id=chosen_meeting_id, appointments=chosen_appointments,
                old_judge=old_judge, old_room=old_room,
                old_day=old_day, new_day=day, # Set the new day
                old_start_timeslot=old_start_timeslot # Keep original start time implicitly
            )
            is_tabu = check_if_move_is_tabu(potential_move, tabu_list)
            if not is_tabu:
                valid_moves.append((potential_move, 0))
            else:
                delta = calculate_delta_score(schedule, potential_move)
                if current_score + delta < best_score:
                    valid_moves.append((potential_move, delta))

    # --- Timeslot Moves ---
    elif move_type == "timeslot":
        for timeslot in range(1, max_start_timeslot_calc + 1):
            if timeslot == old_start_timeslot: continue

            potential_move = Move(
                meeting_id=chosen_meeting_id, appointments=chosen_appointments,
                old_judge=old_judge, old_room=old_room, old_day=old_day,
                old_start_timeslot=old_start_timeslot, new_start_timeslot=timeslot # Set new timeslot
            )
            is_tabu = check_if_move_is_tabu(potential_move, tabu_list)
            if not is_tabu:
                valid_moves.append((potential_move, 0))
            else:
                delta = calculate_delta_score(schedule, potential_move)
                if current_score + delta < best_score:
                    valid_moves.append((potential_move, delta))
                
    # 4. Return the list
    return valid_moves

def generate_random_move_of_random_type(
    schedule: Schedule, 
    compatible_judges_dict: Dict[int, List[Judge]], 
    compatible_rooms_dict: Dict[int, List[Room]]
) -> Move:
    move_type = random.choice(["single", "delete", "insert", "compound"])
    
    if move_type == "single":
        return generate_single_random_move(schedule, compatible_judges_dict, compatible_rooms_dict)
    elif move_type == "delete":
        try:
            return generate_random_delete_move(schedule)
        except ValueError:
            # Fallback to single move if no meetings to delete
            return generate_single_random_move(schedule, compatible_judges_dict, compatible_rooms_dict)
    elif move_type == "insert":
        try:
            return generate_random_insert_move(schedule)
        except ValueError:
            # Fallback to single move if no unplanned meetings
            return generate_single_random_move(schedule, compatible_judges_dict, compatible_rooms_dict)
    else:  # compound
        try:
            return generate_compound_move(schedule, compatible_judges_dict, compatible_rooms_dict)
        except ValueError:
            # Fallback to single move if compound not possible
            return generate_single_random_move(schedule, compatible_judges_dict, compatible_rooms_dict)


def check_room_availability(schedule: Schedule, room_id: int, day: int, start_slot: int, duration_slots: int) -> bool:
    """
    Check if a room is available for a given time range.
    
    Args:
        schedule: The current schedule
        room_id: ID of the room to check
        day: Day to check
        start_slot: Starting timeslot
        duration_slots: Number of timeslots needed
        
    Returns:
        True if room is available for all required timeslots, False otherwise
    """
    for slot_offset in range(duration_slots):
        current_slot = start_slot + slot_offset
        
        # Check if this day/timeslot exists in schedule
        if day in schedule.appointments_by_day_and_timeslot:
            if current_slot in schedule.appointments_by_day_and_timeslot[day]:
                # Check all appointments in this slot
                for appointment in schedule.appointments_by_day_and_timeslot[day][current_slot]:
                    if appointment.room.room_id == room_id:
                        return False  # Room is occupied
    
    return True  # Room is available for all required slots


def generate_contracting_move(schedule: Schedule, debug=False) -> ContractingMove:
    """
    Generate a contracting move that compacts the schedule by moving meetings
    earlier in the day when possible, respecting room availability.
    
    Returns:
        ContractingMove: A compound move containing all individual meeting moves
    """
    contracting_move = ContractingMove()
    
    # Process each judge
    for judge in schedule.get_all_judges():
        # Get all meetings for this judge, sorted by day and timeslot
        judge_meetings = []
        
        # Collect all meetings for this judge
        for meeting_id, appointments in schedule.appointment_chains.items():
            if appointments and appointments[0].judge.judge_id == judge.judge_id:
                first_app = appointments[0]
                judge_meetings.append({
                    'meeting_id': meeting_id,
                    'appointments': appointments,
                    'day': first_app.day,
                    'start_slot': first_app.timeslot_in_day,
                    'duration': len(appointments)
                })
        
        # Sort meetings by day and start timeslot
        judge_meetings.sort(key=lambda m: (m['day'], m['start_slot']))
        
        # Process meetings for each day
        current_day = None
        next_available_slot = 1
        
        for meeting_info in judge_meetings:
            meeting_id = meeting_info['meeting_id']
            appointments = meeting_info['appointments']
            meeting_day = meeting_info['day']
            current_start = meeting_info['start_slot']
            duration = meeting_info['duration']
            
            # Check if we're on a new day
            if meeting_day != current_day:
                current_day = meeting_day
                next_available_slot = 1
            
            # Determine target start slot
            target_start_slot = next_available_slot
            
            # Only try to move if it would actually move the meeting earlier
            if target_start_slot < current_start:
                # Check room availability
                room_id = appointments[0].room.room_id
                
                if check_room_availability(schedule, room_id, meeting_day, target_start_slot, duration):
                    # Create move
                    move = Move(
                        meeting_id=meeting_id,
                        appointments=appointments,
                        old_judge=appointments[0].judge,
                        old_room=appointments[0].room,
                        old_day=meeting_day,
                        old_start_timeslot=current_start,
                        new_start_timeslot=target_start_slot
                    )
                    
                    # Apply the move immediately to update schedule state
                    do_move(move, schedule)
                    contracting_move.add_move(move)
                    
                    # Update next available slot
                    next_available_slot = target_start_slot + duration
                else:
                    # Room conflict - skip this meeting
                    contracting_move.add_skipped(meeting_id, f"Room {room_id} occupied at target slot {target_start_slot}")
                    next_available_slot = current_start + duration
            else:
                # Meeting is already optimally placed or would move later
                contracting_move.add_skipped(meeting_id, "Already optimally placed")
                next_available_slot = current_start + duration
    
    # Mark the contracting move as applied since we applied moves during generation
    contracting_move.is_applied = True
    return contracting_move