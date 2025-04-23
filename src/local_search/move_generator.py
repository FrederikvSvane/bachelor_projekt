import random
from typing import Dict, List

from src.base_model.meeting import Meeting
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.schedule import Schedule
from src.local_search.move import Move
from collections import deque
from src.local_search.rules_engine import calculate_delta_score



def generate_single_move(schedule: Schedule, compatible_judges_dict: Dict[int, List[Judge]], 
                        compatible_rooms_dict: Dict[int, List[Room]]) -> list[Move]:
    """Generate a random valid move"""

    meetings: list[Meeting] = schedule.get_all_meetings()

    if not meetings:
        raise ValueError("No meetings found in the schedule.")
    
    chosen_meeting_id: int = random.choice(meetings).meeting_id
    
    chosen_appointments = sorted(schedule.get_appointment_chain(chosen_meeting_id), key=lambda app: (app.day, app.timeslot_in_day))
    first_appointment = chosen_appointments[0]
    current_day = first_appointment.day
    current_start_timeslot = first_appointment.timeslot_in_day
    
    move = Move(chosen_meeting_id, chosen_appointments)
    move.old_judge = first_appointment.judge
    move.old_room = first_appointment.room
    move.old_day = current_day
    move.old_start_timeslot = current_start_timeslot
    
    # Randomly decide which type of move to make
    n_compatible_judges= len(compatible_judges_dict[chosen_meeting_id])
    n_compatible_rooms = len(compatible_rooms_dict[chosen_meeting_id])
    
    if n_compatible_judges == 1 and n_compatible_rooms == 1:
        move_type = random.choice(["day", "timeslot"])
    elif n_compatible_judges == 1:
        move_type = random.choice(["room", "day", "timeslot"])
    elif n_compatible_rooms == 1:
        move_type = random.choice(["judge", "day", "timeslot"])
    else:
        move_type = random.choice(["judge", "room", "day", "timeslot"])
    
    # Fill in move details based on type
    if move_type == "judge" and compatible_judges_dict[chosen_meeting_id]:
        old_judge = first_appointment.judge
        compatible_judges = compatible_judges_dict[chosen_meeting_id]
        if len(compatible_judges) > 1:  # Ensure there's a different judge to pick
            new_judge = random.choice([j for j in compatible_judges 
                                    if j.judge_id != old_judge.judge_id])
            move.new_judge = new_judge
        else:
            print("No compatible judges")
    
    elif move_type == "room" and compatible_rooms_dict[chosen_meeting_id]:
        old_room = first_appointment.room
        compatible_rooms = compatible_rooms_dict[chosen_meeting_id]
        if len(compatible_rooms) > 1:  # Ensure there's a different room to pick
            new_room = random.choice([r for r in compatible_rooms 
                                    if r.room_id != old_room.room_id])
            move.new_room = new_room
        else:
            print("No compatible rooms")
    
    elif move_type == "day":
        # Pick a new day different from the current day
        valid_days = [d for d in range(1, schedule.work_days + 1) if d != current_day]
        if valid_days:  # Make sure there's at least one other day
            new_day = random.choice(valid_days)
            move.new_day = new_day
        else:
            print("No valid days")
    
    elif move_type == "timeslot":
        # Calculate length of the appointment chain
        meeting_length = len(chosen_appointments)
        
        # Make sure we don't exceed day boundary
        max_start_timeslot = schedule.timeslots_per_work_day - meeting_length + 1
        
        if max_start_timeslot > 1:  # Ensure there's room to move
            # Generate new timeslot different from current
            valid_timeslots = [t for t in range(1, max_start_timeslot + 1) 
                            if t != current_start_timeslot]
            
            if valid_timeslots:  # Make sure there's at least one valid option
                new_start_timeslot = random.choice(valid_timeslots)
                move.new_start_timeslot = new_start_timeslot
            else:
                print("No valid timeslots")
    
    return move

def generate_delete_move(schedule: Schedule, meeting_id: int) -> Move:
    """
    Generate a delete move for a specific meeting ID.
    """
    if meeting_id is None:
        raise ValueError("Meeting ID cannot be None.")
    
    chain_dict = {}
    
    if meeting_id not in chain_dict:
        raise ValueError(f"Meeting ID {meeting_id} not found in schedule.")
    
    chosen_appointments = chain_dict[meeting_id]
    
    if not chosen_appointments:
        raise ValueError(f"No appointments found for meeting ID {meeting_id}.")
    
    first_appointment = chosen_appointments[0]
    day = first_appointment.day
    start_timeslot = first_appointment.timeslot_in_day
    judge = first_appointment.judge
    print(f"Deleting meeting {meeting_id} with judge {judge.judge_id} in room {first_appointment.room.room_id}")
    room = first_appointment.room
    
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

def generate_compound_move(schedule: Schedule, 
                          compatible_judges_dict: Dict[int, List[Judge]], 
                          compatible_rooms_dict: Dict[int, List[Room]],
                          p_j: float = 0.5, p_r: float = 0.5, 
                          p_t: float = 0.5, p_d: float = 0.5) -> Move:
    """
    Generate a move that changes multiple aspects of a meeting based on probabilities.
    Always changes at least two aspects of the meeting.
    
    Args:
        schedule: The current schedule
        compatible_judges_dict: Dict mapping meeting IDs to compatible judges
        compatible_rooms_dict: Dict mapping meeting IDs to compatible rooms
        p_j, p_r, p_d, p_t: Probabilities of changing judge, room, day, timeslot
    
    Returns:
        Move: A move object with AT LEAST two aspects changed
        
    Raises:
        ValueError: If a valid move with at least two changes cannot be created
    """
    # Validate inputs
    if not schedule:
        raise ValueError("No schedule provided")
        
    chain_dict = schedule.appointment_chains
    if not chain_dict:
        raise ValueError("No appointments found in schedule")
    
    if not compatible_judges_dict or not compatible_rooms_dict:
        raise ValueError("No compatible judges or rooms dictionaries provided")
    
    # Select a random meeting
    chosen_meeting_id = random.choice(list(chain_dict.keys()))
    chosen_appointments = chain_dict[chosen_meeting_id]
    
    if not chosen_appointments:
        raise ValueError(f"No appointments found for meeting ID {chosen_meeting_id}")
    
    first_appointment = chosen_appointments[0]
    
    # Create the base move
    move = Move(
        meeting_id=chosen_meeting_id,
        appointments=chosen_appointments,
        old_judge=first_appointment.judge,
        old_room=first_appointment.room,
        old_day=first_appointment.day,
        old_start_timeslot=first_appointment.timeslot_in_day
    )
    
    # Identify changeable aspects with their alternatives and probabilities
    changeable_aspects = []
    
    # Check for alternative judges
    compatible_judges = compatible_judges_dict.get(chosen_meeting_id, [])
    alternative_judges = [j for j in compatible_judges 
                        if j.judge_id != first_appointment.judge.judge_id]
    if alternative_judges:
        changeable_aspects.append(("judge", alternative_judges, p_j))
    
    # Check for alternative rooms
    compatible_rooms = compatible_rooms_dict.get(chosen_meeting_id, [])
    alternative_rooms = [r for r in compatible_rooms 
                        if r.room_id != first_appointment.room.room_id]
    if alternative_rooms:
        changeable_aspects.append(("room", alternative_rooms, p_r))
    
    # Check for alternative days
    valid_days = [d for d in range(1, schedule.work_days + 1) 
                if d != first_appointment.day]
    if valid_days:
        changeable_aspects.append(("day", valid_days, p_d))
    
    # Check for alternative timeslots
    meeting_length = len(chosen_appointments)
    max_start_timeslot = schedule.timeslots_per_work_day - meeting_length + 1
    valid_timeslots = [t for t in range(1, max_start_timeslot + 1) 
                        if t != first_appointment.timeslot_in_day]
    if valid_timeslots:
        changeable_aspects.append(("timeslot", valid_timeslots, p_t))
    
    # Ensure we have at least 2 changeable aspects
    if len(changeable_aspects) < 2:
        raise ValueError(f"Meeting {chosen_meeting_id} does not have at least 2 changeable aspects")
    
    # Apply probabilities and ensure at least 2 aspects change
    selected_aspects = []
    
    # First pass: Apply probabilities
    for aspect_name, alternatives, probability in changeable_aspects:
        if random.random() < probability:
            selected_aspects.append((aspect_name, alternatives))
    
    # Second pass: If we don't have at least 2 aspects, randomly select more
    if len(selected_aspects) < 2:
        # Get aspects not already selected
        remaining_aspects = [(name, alts) for name, alts, _ in changeable_aspects 
                           if name not in [a[0] for a in selected_aspects]]
        
        # How many more do we need?
        additional_needed = 2 - len(selected_aspects)
        
        # Randomly select additional aspects
        random.shuffle(remaining_aspects)
        selected_aspects.extend(remaining_aspects[:additional_needed])
    
    # Final check
    if len(selected_aspects) < 2:
        raise ValueError(f"Unable to create a move with at least 2 changes for meeting {chosen_meeting_id}")
    
    # Apply the changes
    for aspect_name, alternatives in selected_aspects:
        if aspect_name == "judge":
            move.new_judge = random.choice(alternatives)
        elif aspect_name == "room":
            move.new_room = random.choice(alternatives)
        elif aspect_name == "day":
            move.new_day = random.choice(alternatives)
        elif aspect_name == "timeslot":
            move.new_start_timeslot = random.choice(alternatives)
    
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

def generate_list_random_move(schedule: Schedule,
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