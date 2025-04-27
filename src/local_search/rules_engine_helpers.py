from src.base_model.schedule import Schedule
from src.local_search.move import Move
from src.base_model.appointment import Appointment, print_appointments
from collections import defaultdict

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

def get_affected_judge_day_pairs(schedule: Schedule, move: Move) -> set:
    affected_pairs = set()
    original_work_days = schedule.work_days

    if not move.appointments and move.is_insert_move:
        populate_insert_move_appointments(schedule, move)

    old_judge = move.old_judge
    new_judge = move.new_judge if move.new_judge is not None else old_judge
    old_day = move.old_day
    new_day = move.new_day if move.new_day is not None else old_day

    # Add directly affected pairs
    if move.is_delete_move:
        affected_pairs.add((old_day, old_judge.judge_id))
    elif move.is_insert_move:
        affected_pairs.add((new_day, new_judge.judge_id))
    else:
        affected_pairs.add((old_day, old_judge.judge_id))
        if new_day != old_day or new_judge != old_judge:
             affected_pairs.add((new_day, new_judge.judge_id))
        if new_judge != old_judge:
             affected_pairs.add((old_day, new_judge.judge_id))
             affected_pairs.add((new_day, old_judge.judge_id))

    # Calculate the new_last_day if we're deleting from the end
    new_last_day = original_work_days
    
    if move.is_delete_move and old_day == original_work_days:
        # Check if we're removing the only meeting on the last day
        other_meetings_on_last_day = False
        if original_work_days in schedule.appointments_by_day_and_timeslot:
            for ts_apps in schedule.appointments_by_day_and_timeslot[original_work_days].values():
                if any(app not in move.appointments for app in ts_apps):
                    other_meetings_on_last_day = True
                    break
        
        if not other_meetings_on_last_day:
            # Find the new last day by working backwards
            new_last_day = original_work_days - 1
            while new_last_day > 0:
                has_meetings = False
                if new_last_day in schedule.appointments_by_day_and_timeslot:
                    for ts, apps in schedule.appointments_by_day_and_timeslot[new_last_day].items():
                        if apps:
                            has_meetings = True
                            break
                if has_meetings:
                    break
                new_last_day -= 1
            
            # All judges are affected for all trimmed days
            all_judges = schedule.get_all_judges()
            for day in range(new_last_day + 1, original_work_days + 1):
                for judge in all_judges:
                    affected_pairs.add((day, judge.judge_id))
            
            # Also add the new last day for all judges (it's now the boundary)
            if new_last_day > 0:
                for judge in all_judges:
                    affected_pairs.add((new_last_day, judge.judge_id))

    return affected_pairs



def count_unused_timeslots_in_day_for_judge_day_pair(schedule: Schedule, day: int, judge_id: int, is_last_day: bool) -> int:
    used_timeslots = set()
    
    if day in schedule.appointments_by_day_and_timeslot:
        for timeslot in range(1, schedule.timeslots_per_work_day + 1):
            if timeslot in schedule.appointments_by_day_and_timeslot[day]:
                for app in schedule.appointments_by_day_and_timeslot[day][timeslot]:
                    if app.judge.judge_id == judge_id: # TODO vi kunne nok spare nogle loops her, ved at opbevare appointments i en dict med judge_id som key
                        used_timeslots.add(timeslot)
                        break
    
    # hvis det er sidste dag og judge ikke har nogle appointments, så tæller vi ingen unused timeslots
    if is_last_day and not used_timeslots:
        return 0
    
    return schedule.timeslots_per_work_day - len(used_timeslots)


def calculate_unused_timeslots_for_all_judge_day_pairs(schedule: Schedule, affected_pairs: set, current_last_day: int) -> int:
    total_violations = 0
    processed_pairs = set()

    for day, judge_id in affected_pairs:
        if (day, judge_id) in processed_pairs:
            continue
        if day > current_last_day:
             continue

        is_last = (day == current_last_day)
        total_violations += count_unused_timeslots_in_day_for_judge_day_pair(schedule, day, judge_id, is_last)
        processed_pairs.add((day, judge_id))
    return total_violations

def get_appointments_in_timeslot_range_in_day(schedule: Schedule, day, start_timeslot, end_timeslot, judge_id: int = None, meeting_id: int = None) -> list[Appointment]:
    """
    Optionally filter by judge_id (get all appointments for a specific judge).
    Optionally exclude appointments for a specific meeting_id.
    """
    if start_timeslot < 1 or start_timeslot > schedule.timeslots_per_work_day:
        raise ValueError(f"Invalid start timeslot {start_timeslot} for day {day}.")
    if end_timeslot < 1 or end_timeslot > schedule.timeslots_per_work_day:
        raise ValueError(f"Invalid end timeslot {end_timeslot} for day {day}.")
    
    if day not in schedule.appointments_by_day_and_timeslot:
        return []
        
    day_appointments = schedule.appointments_by_day_and_timeslot[day]
    
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
        
        if current_day in schedule.appointments_by_day_and_timeslot and slot_in_day in schedule.appointments_by_day_and_timeslot[current_day]:
            result.extend(schedule.appointments_by_day_and_timeslot[current_day][slot_in_day])
            if judge_id is not None:
                result = [app for app in result if app.judge.judge_id == judge_id]
            if meeting_id is not None:
                result = [app for app in result if app.meeting.meeting_id != meeting_id]
    
    return result


def get_affected_day_timeslot_pairs_for_overbookings(schedule: Schedule, move: Move) -> set:
    affected_pairs = set()
    if move.appointments is None or len(move.appointments) == 0:
        raise ValueError("Move has no appointments.")
    
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
    if day not in schedule.appointments_by_day_and_timeslot or timeslot not in schedule.appointments_by_day_and_timeslot[day]:
        return 0
    
    room_usage = {}
    for app in schedule.appointments_by_day_and_timeslot[day][timeslot]:
        room_id = app.room.room_id
        room_usage[room_id] = room_usage.get(room_id, 0) + 1
    
    # design choice: each room used more than once is 1 violation
    return sum(1 for count in room_usage.values() if count > 1)

def count_judge_overbooking_for_day_timeslot(schedule: Schedule, day: int, timeslot: int) -> int:
    if day not in schedule.appointments_by_day_and_timeslot or timeslot not in schedule.appointments_by_day_and_timeslot[day]:
        return 0
    
    judge_usage = {}
    for app in schedule.appointments_by_day_and_timeslot[day][timeslot]:
        judge_id = app.judge.judge_id
        judge_usage[judge_id] = judge_usage.get(judge_id, 0) + 1

    # design choice: each room used more than once is 1 violation
    return sum(1 for count in judge_usage.values() if count > 1)


def calculate_gaps_between_appointments(schedule: Schedule, judge_id: int, specific_day: int = None):
    total_gaps = 0
    
    days_to_process = [specific_day] if specific_day is not None else range(1, schedule.work_days + 1)
    
    for current_day in days_to_process:
        day_appointments = get_appointments_in_timeslot_range_in_day(
            schedule, current_day, 1, schedule.timeslots_per_work_day, judge_id
        )
        
        if day_appointments:
            occupied_timeslots = {app.timeslot_in_day for app in day_appointments}
            last_timeslot = max(occupied_timeslots)
            total_gaps += last_timeslot - len(occupied_timeslots)
    
    return total_gaps
                
                
def populate_insert_move_appointments(schedule: Schedule, move: Move) -> None:
    """
    Populates an insert move with temporary appointments and sets necessary fields
    WITHOUT MODIFYING the schedule.
    
    Args:
        schedule: The current schedule
        move: The insert move to populate

    """
    move.appointments.clear()
    # Find the meeting in unplanned meetings (for reference only)
    meeting = None
    for m in schedule.get_all_unplanned_meetings():
        if m.meeting_id == move.meeting_id:
            meeting = m
            break
            
    if meeting is None:
        raise ValueError(f"Meeting {move.meeting_id} not found in unplanned meetings")
        
    # Create temporary appointments (not added to schedule)
    meeting_duration_minutes = meeting.meeting_duration
    timeslots_needed = (meeting_duration_minutes // schedule.granularity) + (1 if meeting_duration_minutes % schedule.granularity > 0 else 0)
    
    if timeslots_needed > schedule.timeslots_per_work_day or timeslots_needed <= 0:
        raise ValueError(f"Meeting {meeting.meeting_id} requires {timeslots_needed} timeslots, which is invalid.")
        
    
    temp_appointments = []
    for i in range(timeslots_needed):
        global_timeslot = ((move.new_day - 1) * schedule.timeslots_per_work_day) + move.new_start_timeslot + i
        day = ((global_timeslot - 1) // schedule.timeslots_per_work_day) + 1
        timeslot_in_day = ((global_timeslot - 1) % schedule.timeslots_per_work_day) + 1
        
        appointment = Appointment(
            meeting=meeting,
            judge=move.new_judge,
            room=move.new_room,
            day=day,
            timeslot_in_day=timeslot_in_day
        )
        
        temp_appointments.append(appointment)
    
    move.appointments = temp_appointments

    # Ensure the old values are set to None    
    move.old_judge = None
    move.old_room = None
    move.old_day = None
    move.old_start_timeslot = None