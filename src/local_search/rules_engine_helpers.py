from src.base_model.schedule import Schedule
from src.local_search.move import Move
from src.base_model.appointment import Appointment
from collections import defaultdict
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
    # Get all appointments for this judge on this day
    appointments_in_day_for_judge = get_appointments_in_timeslot_range_in_day(
        schedule=schedule,
        day=day,
        start_timeslot=1,
        end_timeslot=schedule.timeslots_per_work_day,
        judge_id=judge_id
    )
    
    # Group room IDs by timeslotsnake
    rooms_by_timeslot = defaultdict(set)
    for app in appointments_in_day_for_judge:
        rooms_by_timeslot[app.timeslot_in_day].add(app.room.room_id)
    
    # Get occupied timeslots and sort them
    occupied_timeslots = sorted(rooms_by_timeslot.keys())
    
    # Early return if fewer than 2 occupied timeslots
    if len(occupied_timeslots) < 2:
        return 0
    
    violations = 0
    prev_rooms = rooms_by_timeslot[occupied_timeslots[0]]
    
    for timeslot in occupied_timeslots[1:]:
        current_rooms = rooms_by_timeslot[timeslot]
        if prev_rooms != current_rooms:
            violations += 1
        prev_rooms = current_rooms
    
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
                    if app.judge.judge_id == judge_id: # TODO vi kunne nok spare nogle loops her, ved at opbevare appointments i en dict med judge_id som key
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
    
    if day not in schedule.appointments_by_day:
        return []
        
    day_appointments = schedule.appointments_by_day[day]
    
    # Single list comprehension with all filtering conditions
    return [
        app 
        for timeslot in range(start_timeslot, end_timeslot + 1) 
        if timeslot in day_appointments
        for app in day_appointments[timeslot]
        if (judge_id is None or app.judge.judge_id == judge_id) and 
           (meeting_id is None or app.meeting.meeting_id != meeting_id)
    ]
            
        
        

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


def get_affected_day_timeslot_pairs_for_overbookings(schedule: Schedule, move: Move) -> set:
    affected_pairs = set()
    
    for app in move.appointments:
        affected_pairs.add((app.day, app.timeslot_in_day))
    
    if move.new_day is not None or move.new_start_timeslot is not None:
        start_day = move.new_day if move.new_day is not None else move.old_day
        start_timeslot = move.new_start_timeslot if move.new_start_timeslot is not None else move.old_start_timeslot
        
        for i in range(len(move.appointments)):
            global_timeslot = ((start_day - 1) * schedule.timeslots_per_work_day) + start_timeslot + i
            new_day = ((global_timeslot - 1) // schedule.timeslots_per_work_day) + 1
            new_timeslot = ((global_timeslot - 1) % schedule.timeslots_per_work_day) + 1
            affected_pairs.add((new_day, new_timeslot))
    
    return affected_pairs

def count_room_overbooking_for_day_timeslot(schedule: Schedule, day: int, timeslot: int) -> int:
    if day not in schedule.appointments_by_day or timeslot not in schedule.appointments_by_day[day]:
        return 0
    
    room_usage = {}
    for app in schedule.appointments_by_day[day][timeslot]:
        room_id = app.room.room_id
        room_usage[room_id] = room_usage.get(room_id, 0) + 1
    
    # design choice: each room used more than once is 1 violation
    return sum(1 for count in room_usage.values() if count > 1)

def count_judge_overbooking_for_day_timeslot(schedule: Schedule, day: int, timeslot: int) -> int:
    if day not in schedule.appointments_by_day or timeslot not in schedule.appointments_by_day[day]:
        return 0
    
    judge_usage = {}
    for app in schedule.appointments_by_day[day][timeslot]:
        judge_id = app.judge.judge_id
        judge_usage[judge_id] = judge_usage.get(judge_id, 0) + 1

    # design choice: each room used more than once is 1 violation
    return sum(1 for count in judge_usage.values() if count > 1)