import random
from typing import Dict, List

from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.schedule import Schedule
from src.base_model.compatibility_checks import case_judge_compatible, case_room_compatible
from src.local_search.move import Move

def calculate_compatible_judges(cases: List[Case], judges: List[Judge]) -> Dict[int, List[Judge]]:
    compatible_judges = {}
    for case in cases:
        compatible_judges[case.case_id] = [judge for judge in judges 
                                          if case_judge_compatible(case, judge)]
        
    return compatible_judges

def calculate_compatible_rooms(cases: List[Case], rooms: List[Room]) -> Dict[int, List[Room]]:
    compatible_rooms = {}
    for case in cases:
        compatible_rooms[case.case_id] = [room for room in rooms 
                                         if case_room_compatible(case, room)]
        
    return compatible_rooms

def identify_appointment_chains(schedule: Schedule) -> Dict:
    """
    Identify chains of appointments representing the same case.
    """
    appointment_chains = {}  # Key: case_id, Value: list of appointments
    
    for appointment in schedule.appointments:
        key = appointment.case.case_id
        if key not in appointment_chains:
            appointment_chains[key] = []
        appointment_chains[key].append(appointment)
    
    # Sort each chain by day and timeslot
    for key, appointments in appointment_chains.items():
        appointments.sort(key=lambda app: (app.day, app.timeslot_in_day))
    
    return appointment_chains

def generate_random_move(schedule: Schedule, compatible_judges_dict: Dict[int, List[Judge]], 
                        compatible_rooms_dict: Dict[int, List[Room]]) -> Move:
    """Generate a random valid move"""
    # Select a random case and its appointments
    chain_dict = identify_appointment_chains(schedule)
    chosen_case_id = random.choice(list(chain_dict.keys()))
    
    # Sort appointments by day and timeslot
    chosen_appointments = sorted(chain_dict[chosen_case_id], 
                               key=lambda app: (app.day, app.timeslot_in_day))
    
    # Get current values
    first_app = chosen_appointments[0]
    current_day = first_app.day
    current_start_timeslot = first_app.timeslot_in_day
    
    # Initialize move object
    move = Move(chosen_case_id, chosen_appointments, 
               timeslots_per_day=schedule.timeslots_per_work_day)
    
    # Randomly decide which type of move to make
    n_compatible_judges= len(compatible_judges_dict[chosen_case_id])
    n_compatible_rooms = len(compatible_rooms_dict[chosen_case_id])
    if n_compatible_judges == 1 and n_compatible_rooms == 1:
        move_type = random.choice(["day", "timeslot"])
    elif n_compatible_judges == 1:
        move_type = random.choice(["room", "day", "timeslot"])
    elif n_compatible_rooms == 1:
        move_type = random.choice(["judge", "day", "timeslot"])
    else:
        move_type = random.choice(["judge", "room", "day", "timeslot"])
    
    # Fill in move details based on type
    if move_type == "judge" and compatible_judges_dict[chosen_case_id]:
        old_judge = first_app.judge
        compatible_judges = compatible_judges_dict[chosen_case_id]
        if len(compatible_judges) > 1:  # Ensure there's a different judge to pick
            new_judge = random.choice([j for j in compatible_judges 
                                     if j.judge_id != old_judge.judge_id])
            move.old_judge = old_judge
            move.new_judge = new_judge
        else:
            print("No compatible judges")
    
    elif move_type == "room" and compatible_rooms_dict[chosen_case_id]:
        old_room = first_app.room
        compatible_rooms = compatible_rooms_dict[chosen_case_id]
        if len(compatible_rooms) > 1:  # Ensure there's a different room to pick
            new_room = random.choice([r for r in compatible_rooms 
                                    if r.room_id != old_room.room_id])
            move.old_room = old_room
            move.new_room = new_room
        else:
            print("No compatible rooms")
    
    elif move_type == "day":
        # Pick a new day different from the current day
        valid_days = [d for d in range(1, schedule.work_days + 1) if d != current_day]
        if valid_days:  # Make sure there's at least one other day
            new_day = random.choice(valid_days)
            move.old_day = current_day
            move.new_day = new_day
        else:
            print("No valid days")
    
    elif move_type == "timeslot":
        # Calculate length of the appointment chain
        case_length = len(chosen_appointments)
        
        # Make sure we don't exceed day boundary
        max_start_timeslot = schedule.timeslots_per_work_day - case_length + 1
        
        if max_start_timeslot > 1:  # Ensure there's room to move
            # Generate new timeslot different from current
            valid_timeslots = [t for t in range(1, max_start_timeslot + 1) 
                             if t != current_start_timeslot]
            
            if valid_timeslots:  # Make sure there's at least one valid option
                new_start_timeslot = random.choice(valid_timeslots)
                move.old_start_timeslot = current_start_timeslot
                move.new_start_timeslot = new_start_timeslot
            else:
                print("No valid timeslots")
    
    return move