from collections import defaultdict
from src.base_model.schedule import Schedule
from src.base_model.appointment import Appointment
from src.base_model.compatibility_checks import check_case_judge_compatibility, check_case_room_compatibility, check_judge_room_compatibility
from src.local_search.move import Move, do_move, undo_move
from sys import exit

def calculate_delta_score(schedule: Schedule, move: Move) -> int:
    """
    do the move AFTER calling this function.
    NOT BEFORE!!!
    """
    if move is None or move.old_judge is None or move.old_room is None or move.old_start_timeslot is None or move.old_day is None:
        print("cant work with this move. set the old values to something that isnt None")
        exit()
    if move.is_applied:
        print("fuck you. read the function description")
        exit()
    
    violations = 0
    
    violations += room_stability_per_day_delta(schedule, move)
    
    return 0

def calculate_full_score(schedule: Schedule) -> int:
    score = 0
    
    
        
    return score


def room_stability_per_day_full(schedule: Schedule) -> int:
    """
    returns the total amount of room changes that all judges make, day by day.
    that is, the amount of VIOLATIONS! not a score!
    """
    score = 0
    by_day_judge = {}
    for app in schedule.appointments:
        key = (app.day, app.judge.judge_id)
        if key not in by_day_judge:
            by_day_judge[key] = []
        by_day_judge[key].append(app)
        
    for (_, _), apps in by_day_judge.items():
        apps.sort(key=lambda a: a.timeslot_in_day)
        current_room = None

        for app in apps:
            if current_room is not None and app.room.room_id != current_room:
                score += 1
            current_room = app.room.room_id
    
    return score

def room_stability_per_day_delta(schedule: Schedule, move: Move) -> int:
    """
    returns amount of VIOLATIONS! not score!
    """
    # room stability can be affected by changing the timeslot, day, judge or room (yes, any of them)
    timeslot_delta, day_delta, judge_delta, room_delta = 0, 0, 0, 0
    
    is_union_move = sum([
        move.new_start_timeslot is not None,
        move.new_day is not None,
        move.new_judge is not None,
        move.new_room is not None
    ]) > 1
    
    if move.new_start_timeslot:
        print("TIMESLOT MOVE")
    if move.new_day:
        print("DAY MOVE")
    if move.new_judge:
        print("JUDGE MOVE")
    if move.new_room:
        print("ROOM MOVE")
    
    if is_union_move:
        print("UNION MOVE")
        return room_stability_per_day_full(schedule)
    
    elif move.new_start_timeslot is not None:
        # if timeslot is changed, the room stability is only affected for one judge and one day
        judgeid = move.old_judge.judge_id
        day = move.old_day
        
        old_stability_violations = count_room_changes_for_judge_on_specific_day(schedule, move, judgeid, day)
        do_move(move)
        new_stability_violations = count_room_changes_for_judge_on_specific_day(schedule, move, judgeid, day)
        undo_move(move)
        
        timeslot_delta = new_stability_violations - old_stability_violations
        
    elif move.new_day is not None:
        # if day is changed, the room stability is affected from one judge and two days
        judgeid = move.old_judge.judge_id
        old_day = move.old_day
        new_day = move.new_day
        
        old_stability_violations_old_day = count_room_changes_for_judge_on_specific_day(schedule, move, judgeid, old_day)
        old_stability_violations_new_day = count_room_changes_for_judge_on_specific_day(schedule, move, judgeid, new_day)
        do_move(move)
        new_stability_violations_old_day = count_room_changes_for_judge_on_specific_day(schedule, move, judgeid, old_day)
        new_stability_violations_new_day = count_room_changes_for_judge_on_specific_day(schedule, move, judgeid, new_day)
        undo_move(move)
        
        print(f"old old day: {old_stability_violations_old_day}, old new day: {old_stability_violations_new_day}")
        print(f"new old day: {new_stability_violations_old_day}, new new day: {new_stability_violations_new_day}")
        
        old_stability_violations = old_stability_violations_old_day + old_stability_violations_new_day
        new_stability_violations = new_stability_violations_old_day + new_stability_violations_new_day
        
        print(f"old: {old_stability_violations}, new: {new_stability_violations}")
        
        day_delta = new_stability_violations - old_stability_violations
        print(f"day delta: {day_delta}")
        
    elif move.new_judge is not None:
        # if judge is changed, the room stability is affected for two judges and one day  
        old_judgeid = move.old_judge.judge_id
        new_judgeid = move.new_judge.judge_id
        day = move.old_day
        
        old_stability_violations_old_judge = count_room_changes_for_judge_on_specific_day(schedule, move, old_judgeid, day)
        old_stability_violations_new_judge = count_room_changes_for_judge_on_specific_day(schedule, move, new_judgeid, day)
        do_move(move)
        new_stability_violations_old_judge = count_room_changes_for_judge_on_specific_day(schedule, move, old_judgeid, day)
        new_stability_violations_new_judge = count_room_changes_for_judge_on_specific_day(schedule, move, new_judgeid, day)
        undo_move(move)
        
        old_stability_violations = old_stability_violations_old_judge + old_stability_violations_new_judge
        new_stability_violations = new_stability_violations_old_judge + new_stability_violations_new_judge
        
        judge_delta = new_stability_violations - old_stability_violations
    
    elif move.new_room is not None:
        # if room is changed, the room stability is affected for one judge and one day
        judgeid = move.old_judge.judge_id
        day = move.old_day
        
        old_stability_violations = count_room_changes_for_judge_on_specific_day(schedule, move, judgeid, day)
        do_move(move)
        
        new_stability_violations = count_room_changes_for_judge_on_specific_day(schedule, move, judgeid, day)
        undo_move(move)
        
        room_delta = new_stability_violations - old_stability_violations
    
    print(f"timeslot delta: {timeslot_delta}, day delta: {day_delta}, judge delta: {judge_delta}, room delta: {room_delta}")
    return timeslot_delta + day_delta + judge_delta + room_delta
    
        
        
def count_room_changes_for_judge_on_specific_day(schedule: Schedule, move: Move, judge_id: int, day: int) -> int:
    # here we want to loop through all appointments for the judge on the day and count how many times the room changes
    
    # since the move has not modified the schedule, we need to remove the appointments that the move represents, because are not accurately represented in the schedule
    scheduled_appointments_without_move_appointments = [app for app in schedule.appointments if judge_id == app.judge.judge_id and day == app.day and app.meeting.meeting_id != move.meeting_id]

    # then we add the appointments that the move represents
    appointments_in_move_chain = [app for app in move.appointments if judge_id == app.judge.judge_id and day == app.day]
    appointments = scheduled_appointments_without_move_appointments + appointments_in_move_chain

    appointments.sort(key=lambda a: a.timeslot_in_day)
    
    room_changes = 0
    current_room = None
    for app in appointments:
        if current_room is not None and app.room.room_id != current_room:
            print(f"appoinment: {app}")
            print(f"room change for judge {judge_id} on day {day} at timeslot {app.timeslot_in_day}")
            room_changes += 1
        current_room = app.room.room_id

    return room_changes
    

def unused_timeslots(schedule: Schedule, move: Move, initial_calculation: bool) -> int:
    """
    Counts the number of unused timeblocks in the schedule.
    Only calculates delta when the move affects the latest timeslot.
    """
    if initial_calculation:
        # Get all judges
        all_judge_ids = schedule.get_all_judges()
        
        # Find latest global timeslot
        latest_global_timeslot = 0
        apps_descending = sorted(schedule.appointments, key=lambda app: app.day * schedule.timeslots_per_work_day + app.timeslot_in_day, reverse=True)
        for app in schedule.appointments:
            global_timeslot = (app.day - 1) * schedule.timeslots_per_work_day + app.timeslot_in_day
            latest_global_timeslot = max(latest_global_timeslot, global_timeslot)
        
        # Track used timeslots
        used_global_slots = set()
        for app in schedule.appointments:
            judge_id = app.judge.judge_id
            global_timeslot = (app.day - 1) * schedule.timeslots_per_work_day + app.timeslot_in_day
            used_global_slots.add((judge_id, global_timeslot))
        
        # Count unused slots
        unused_slots = 0
        for judge_id in all_judge_ids:
            for global_timeslot in range(1, latest_global_timeslot + 1):
                if (judge_id, global_timeslot) not in used_global_slots:
                    unused_slots += 1
        
        return unused_slots
    
    # Delta calculation path - only relevant if we change the schedule length!
    elif move is not None and (move.new_start_timeslot is not None or move.new_day is not None):
        # 1. Find current latest timeslot in schedule
        current_latest = 0
        latest_app = None
        
        for app in schedule.appointments:
            global_slot = (app.day - 1) * schedule.timeslots_per_work_day + app.timeslot_in_day
            if global_slot > current_latest:
                current_latest = global_slot
                latest_app = app
        
        # 2. Check if we're moving what was previously the latest appointment
        move_contains_latest = any(app.meeting.meeting_id == latest_app.meeting.meeting_id for app in move.appointments)
        
        # 3. Calculate what will be the latest timeslot after the move
        new_day = move.new_day if move.new_day is not None else move.appointments[0].day
        new_latest = 0
        
        if move.new_start_timeslot is not None:
            # Calculate the last timeslot of the moved appointment chain
            last_offset = len(move.appointments) - 1
            new_latest_from_move = (new_day - 1) * schedule.timeslots_per_work_day + (move.new_start_timeslot + last_offset)
            
            # If we're moving the latest appointment, the new schedule latest 
            # will be the maximum of this move's latest and the previous 2nd latest
            if move_contains_latest:
                # Find second latest appointment (simple approach)
                second_latest = 0
                for app in schedule.appointments:
                    if any(a.meeting.meeting_id == app.meeting.meeting_id for a in move.appointments):
                        continue  # Skip appointments in the move
                    global_slot = (app.day - 1) * schedule.timeslots_per_work_day + app.timeslot_in_day
                    second_latest = max(second_latest, global_slot)
                
                new_latest = max(new_latest_from_move, second_latest)
            else:
                # If we're not moving the latest appointment, the new latest
                # will be the maximum of the current latest and this move's latest
                new_latest = max(current_latest, new_latest_from_move)
            
            # 4. Calculate delta based on the change in the schedule length
            judge_count = max(app.judge.judge_id for app in schedule.appointments)
            
            if new_latest > current_latest:
                # Schedule got longer - add (new-current) slots for each judge
                return judge_count * (new_latest - current_latest)
            elif new_latest < current_latest:
                # Schedule got shorter - remove (current-new) slots for each judge
                return -judge_count * (current_latest - new_latest)
    
    # No change in schedule length = no change in unused slots
    return 0

def schedule_length(schedule: Schedule, move: Move, initial_calculation: bool) -> int:
    """
    Calculate the total length of the schedule in timeslots.
    """
    # Full calculation path
    if initial_calculation:
        return max(schedule.timeslots_per_work_day * (app.day-1) + app.timeslot_in_day 
                  for app in schedule.appointments)
    
    # Delta calculation path
    elif move is not None and (move.new_start_timeslot is not None or move.new_day is not None):
        current_max = max(schedule.timeslots_per_work_day * (app.day-1) + app.timeslot_in_day 
                         for app in schedule.appointments)
        
        # Calculate max timeslot after move
        new_day = move.new_day if move.new_day is not None else move.appointments[0].day
        
        if move.new_start_timeslot is not None:
            last_offset = len(move.appointments) - 1
            new_max_slot = schedule.timeslots_per_work_day * (new_day-1) + (move.new_start_timeslot + last_offset)
            
            # Return delta (new_max - current_max) if larger, else 0
            return max(0, new_max_slot - current_max)
    
    # No relevant change
    return 0

def case_planned_longer_than_day(schedule: Schedule, move: Move, initial_calculation) -> int: 
    """
    Check if a case is planned both at the end of day x and start of day y.
    Apply penalty only once per case.
    """
    if initial_calculation or (move is not None and (move.new_start_timeslot is not None or move.new_day is not None)):
        score = 0
        
        # Group timeslots by case_id
        meeting_timeslots = defaultdict(set)
        for app in schedule.appointments:
            meeting_timeslots[app.meeting.meeting_id].add(app.timeslot_in_day)
        
        # Check each case
        for meeting_id, timeslots in meeting_timeslots.items():
            # Check each day boundary
            for day in range(schedule.work_days - 1):
                last_slot_of_day = (day + 1) * schedule.timeslots_per_work_day - 1
                first_slot_of_next_day = (day + 1) * schedule.timeslots_per_work_day
                
                # If case has appointments on both sides of boundary, penalize it
                if last_slot_of_day in timeslots and first_slot_of_next_day in timeslots:
                    #print(f"Case {case_id} scheduled longer than the day: timeslots {last_slot_of_day} and {first_slot_of_next_day}")
                    score += 10
                    break  # Only penalize once per case
        
        return score
    return 0

def overbooked_room_in_timeslot(schedule: Schedule, move, initial_calculation) -> int:
    return check_hard_constraint(schedule, move, initial_calculation)["overbooked_room_in_timeslot"]

def overbooked_judge_in_timeslot(schedule: Schedule, move, initial_calculation) -> int:
    return check_hard_constraint(schedule, move, initial_calculation)["overbooked_judge_in_timeslot"]

def judge_case_compatibility(schedule: Schedule, move, initial_calculation) -> int:
    return check_hard_constraint(schedule, move, initial_calculation)["judge_case_compatibility"]

def judge_room_compatiblity(schedule: Schedule, move, initial_calculation) -> int:
    return check_hard_constraint(schedule, move, initial_calculation)["judge_room_compatiblity"]

def case_room_compatibility(schedule: Schedule, move, initial_calculation) -> int:
    return check_hard_constraint(schedule, move, initial_calculation)["case_room_compatibility"]

def check_hard_constraint(schedule: Schedule, move: Move, initial_calculation) -> dict:
    """
    Efficiently checks hard scheduling constraints with delta support
    Returns a dictionary with penalties for each constraint
    """
    penalties = {
        "overbooked_room_in_timeslot": 0,
        "overbooked_judge_in_timeslot": 0,
        "judge_case_compatibility": 0,
        "judge_room_compatiblity": 0,
        "case_room_compatibility": 0
    }
    
    # Full calculation path
    if initial_calculation:
        room_usage = {}  # (room_id, day, timeslot) -> count
        judge_usage = {}  # (judge_id, day, timeslot) -> count
        
        for app in schedule.appointments:
            room_key = (app.room.room_id, app.day, app.timeslot_in_day)
            if room_key in room_usage:
                room_usage[room_key] += 1
            else:
                room_usage[room_key] = 1
                
            judge_key = (app.judge.judge_id, app.day, app.timeslot_in_day)
            if judge_key in judge_usage:
                judge_usage[judge_key] += 1
            else:
                judge_usage[judge_key] = 1
            
            if not check_case_judge_compatibility(app.meeting.case.case_id, app.judge.judge_id):
                penalties["judge_case_compatibility"] = 1000
                
            if not check_judge_room_compatibility(app.judge.judge_id, app.room.room_id):
                penalties["judge_room_compatiblity"] = 1000
                
            if not check_case_room_compatibility(app.meeting.case.case_id, app.room.room_id):
                penalties["case_room_compatibility"] = 1000
        
        for count in room_usage.values():
            if count > 1:
                penalties["overbooked_room_in_timeslot"] += 1000 * (count - 1)
                
        for count in judge_usage.values():
            if count > 1:
                penalties["overbooked_judge_in_timeslot"] += 1000 * (count - 1)
    
    
    # Delta calculation path
    elif move is not None and move.appointments:
        if move.new_judge:
            for app in move.appointments:
                if not check_case_judge_compatibility(app.meeting.case.case_id, move.new_judge.judge_id):
                    penalties["judge_case_compatibility"] = 1000
                    break
            
            for app in move.appointments:
                room_id = move.new_room.room_id if move.new_room else app.room.room_id
                if not check_judge_room_compatibility(move.new_judge.judge_id, room_id):
                    penalties["judge_room_compatiblity"] = 1000
                    break
        
        if move.new_room:
            for app in move.appointments:
                if not check_case_room_compatibility(app.meeting.case.case_id, move.new_room.room_id):
                    penalties["case_room_compatibility"] = 1000
                    break
            
            for app in move.appointments:
                judge_id = move.new_judge.judge_id if move.new_judge else app.judge.judge_id
                if not check_judge_room_compatibility(judge_id, move.new_room.room_id):
                    penalties["judge_room_compatiblity"] = 1000
                    break
        
        affected_slots = set() # only checking the timeslots affected by the move
        for app in move.appointments:
            day = move.new_day if move.new_day is not None else app.day
            
            if move.new_start_timeslot is not None:
                idx = move.appointments.index(app)
                timeslot = move.new_start_timeslot + idx
            else:
                timeslot = app.timeslot_in_day
            
            affected_slots.add((day, timeslot))
        
        for day, timeslot in affected_slots:
            if move.new_room and not move.is_applied:
                room_conflicts = sum(1 for a in schedule.appointments 
                                    if a.day == day and a.timeslot_in_day == timeslot and 
                                    a.room.room_id == move.new_room.room_id and
                                    a.meeting.meeting_id != move.meeting_id)
                if room_conflicts > 0:
                    penalties["overbooked_room_in_timeslot"] += 1000
            
            if move.new_judge and not move.is_applied:
                judge_conflicts = sum(1 for a in schedule.appointments 
                                        if a.day == day and a.timeslot_in_day == timeslot and 
                                        a.judge.judge_id == move.new_judge.judge_id and
                                        a.meeting.meeting_id != move.meeting_id)
                if judge_conflicts > 0:
                    penalties["overbooked_judge_in_timeslot"] += 1000
    
    return penalties