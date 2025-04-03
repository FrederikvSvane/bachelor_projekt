from src.base_model.schedule import Schedule
from src.local_search.move import Move
from src.base_model.appointment import Appointment
from sys import exit

def get_affected_pairs_for_room_stability(schedule: Schedule, move: Move):
    affected_day_judge_pairs = set()
    
    affected_day_judge_pairs.add((move.old_day, move.old_judge.judge_id)) # original day and judge

    if move.new_day is not None:
        affected_day_judge_pairs.add((move.new_day, move.old_judge.judge_id))
    
    if move.new_judge is not None:
        affected_day_judge_pairs.add((move.old_day, move.new_judge.judge_id))
    
    if move.new_day is not None and move.new_judge is not None:
        affected_day_judge_pairs.add((move.new_day, move.new_judge.judge_id))
    
    is_overlapping_day_boundary = move.appointments[0].day != move.appointments[-1].day
    
    if is_overlapping_day_boundary:
        start_day = move.new_day if move.new_day is not None else move.old_day
        start_timeslot = move.new_start_timeslot if move.new_start_timeslot is not None else move.old_start_timeslot
        judge_id = move.new_judge.judge_id if move.new_judge is not None else move.old_judge.judge_id

        for i in range(len(move.appointments)):
            global_timeslot = ((start_day - 1) * schedule.timeslots_per_work_day) + start_timeslot + i
            new_day = ((global_timeslot - 1) // schedule.timeslots_per_work_day) + 1
            affected_day_judge_pairs.add((new_day, judge_id))
        
    return affected_day_judge_pairs

def count_room_changes_for_day_judge_pair(schedule: Schedule, day: int, judge_id: int):
    appointments_in_day = get_appointments_in_timeslot_range_in_day(schedule=schedule, day=day, start_timeslot=1, end_timeslot=schedule.timeslots_per_work_day, judge_id=judge_id)

    appointments_in_day.sort(key=lambda a: (a.timeslot_in_day, a.meeting.meeting_id, a.room.room_id))

    current_room_id = None
    violations = 0
    for appointment in appointments_in_day:
        if current_room_id is not None and appointment.room.room_id != current_room_id:
            violations += 1
        current_room_id = appointment.room.room_id
    
    return violations

def get_affected_judge_day_pairs_for_unused_timegrains(schedule: Schedule, move: Move) -> set:
    affected_pairs = set()
    
    affected_pairs.add((move.old_day, move.old_judge.judge_id))
    if move.new_day is not None:
        affected_pairs.add((move.new_day, move.old_judge.judge_id))
    
    if move.new_judge is not None:
        affected_pairs.add((move.old_day, move.new_judge.judge_id))
        if move.new_day is not None:
            affected_pairs.add((move.new_day, move.new_judge.judge_id))
    
    last_day = schedule.work_days
    if move.old_day == last_day or (move.new_day is not None and move.new_day >= last_day):
        for judge in schedule.get_all_judges():
            affected_pairs.add((last_day, judge.judge_id))
            
    return affected_pairs


def count_unused_timeslots_in_day_for_judge_day_pair(schedule: Schedule, day: int, judge_id: int, is_last_day: bool) -> int:
    used_timeslots = set()
    
    if day in schedule.appointments_by_day:
        for timeslot in range(1, schedule.timeslots_per_work_day + 1):
            if timeslot in schedule.appointments_by_day[day]:
                for app in schedule.appointments_by_day[day][timeslot]:
                    if app.judge.judge_id == judge_id:
                        used_timeslots.add(timeslot)
                        break
    
    # hvis det er sidste dag og judge ikke har nogle appointments, så tæller vi ingen unused timeslots
    if is_last_day and not used_timeslots:
        return 0
    
    return schedule.timeslots_per_work_day - len(used_timeslots)


def calculate_unused_timeslots_for_all_judge_day_pairs(schedule: Schedule, affected_pairs: set, last_day: int) -> int:
    total_violations = 0
    for day, judge_id in affected_pairs:
        is_last_day = (day == last_day)
        total_violations += count_unused_timeslots_in_day_for_judge_day_pair(schedule, day, judge_id, is_last_day)
    return total_violations


def get_latest_global_timeslot(schedule):
    for day in range(schedule.work_days, 0, -1):
        if day not in schedule.appointments_by_day:
            continue
        for timeslot in range(schedule.timeslots_per_work_day, 0, -1):
            if timeslot not in schedule.appointments_by_day[day]:
                continue
            if schedule.appointments_by_day[day][timeslot]:  
                return (day - 1) * schedule.timeslots_per_work_day + timeslot
    
    return 0 # should only happen if schedule is empty

def get_n_unused_timeslots_in_range(schedule: Schedule, start_day: int, end_day: int, start_timeslot: int, end_timeslot: int, judge_id: int = None, meeting_id: int = None): #FIXME take a move as input insted of start, end day, start, end timeslot
    # Calculate global start and end timeslots
    global_start = ((start_day - 1) * schedule.timeslots_per_work_day) + start_timeslot
    global_end = ((end_day - 1) * schedule.timeslots_per_work_day) + end_timeslot
    
    # Ensure we don't exceed the total available timeslots
    total_timeslots = schedule.work_days * schedule.timeslots_per_work_day
    global_end = min(global_end, total_timeslots)
    
    # Get all judges if not specified
    if judge_id is None:
        judges = schedule.get_all_judges()
    else:
        # Create a list with just the specified judge
        judges = [j for j in schedule.get_all_judges() if j.judge_id == judge_id]
    
    # Track used slots as (judge_id, global_timeslot) pairs like in the full function
    used_global_slots = set()
    
    # For each timeslot in range
    for global_timeslot in range(global_start, global_end + 1):
        # Convert global timeslot to day and timeslot within day
        day = ((global_timeslot - 1) // schedule.timeslots_per_work_day) + 1
        timeslot_in_day = ((global_timeslot - 1) % schedule.timeslots_per_work_day) + 1
        
        # If this day and timeslot exist in the schedule
        if day in schedule.appointments_by_day and timeslot_in_day in schedule.appointments_by_day[day]:
            for appointment in schedule.appointments_by_day[day][timeslot_in_day]:
                if meeting_id is not None and appointment.meeting.meeting_id == meeting_id:
                    continue
                # Only track the specified judge(s)
                if judge_id is None or appointment.judge.judge_id == judge_id:
                    used_global_slots.add((appointment.judge.judge_id, global_timeslot))
                    
    
    # Calculate total possible slots (same logic as full function)
    total_possible_slots = len(judges) * (global_end - global_start + 1)
    
    # Return number of unused slots
    return total_possible_slots - len(used_global_slots)

def get_appointments_in_timeslot_range_in_day(schedule: Schedule, day, start_timeslot, end_timeslot, judge_id: int = None, meeting_id: int = None) -> list[Appointment]:
    """
    Optionally filter by judge_id (get all appointments for a specific judge).
    Optionally exclude appointments for a specific meeting_id.
    """
    if start_timeslot < 1 or start_timeslot > schedule.timeslots_per_work_day:
        print(f"Invalid start timeslot {start_timeslot} for day {day}.")
        exit()
    if end_timeslot < 1 or end_timeslot > schedule.timeslots_per_work_day:
        print(f"Invalid end timeslot {end_timeslot} for day {day}.")
        exit()
    
    result = []
    
    for timeslot in range(start_timeslot, end_timeslot + 1):
        if day in schedule.appointments_by_day and timeslot in schedule.appointments_by_day[day]:
            result.extend(schedule.appointments_by_day[day][timeslot])
            if judge_id is not None:
                result = [app for app in result if app.judge.judge_id == judge_id]
            if meeting_id is not None:
                result = [app for app in result if app.meeting.meeting_id != meeting_id]
    
    return result
            
        
        

def get_appointments_in_timeslot_range(schedule: Schedule, start_day, start_slot, end_slot, judge_id: int = None, meeting_id: int = None) -> list[Appointment]:
    """
    Get all appointments within a specific timeslot range for a given day.
    Optionally filter by judge_id (get all appointments for a specific judge).
    Optionally exclude appointments for a specific meeting_id.
    """
    result = []
    
    global_start = ((start_day - 1) * schedule.timeslots_per_work_day) + start_slot
    global_end = ((start_day - 1) * schedule.timeslots_per_work_day) + end_slot
    
    for global_slot in range(global_start, global_end + 1):
        current_day = ((global_slot - 1) // schedule.timeslots_per_work_day) + 1
        slot_in_day = ((global_slot - 1) % schedule.timeslots_per_work_day) + 1
        
        if current_day in schedule.appointments_by_day and slot_in_day in schedule.appointments_by_day[current_day]:
            result.extend(schedule.appointments_by_day[current_day][slot_in_day])
            if judge_id is not None:
                result = [app for app in result if app.judge.judge_id == judge_id]
            if meeting_id is not None:
                result = [app for app in result if app.meeting.meeting_id != meeting_id]
                
    
    return result