from collections import defaultdict
from src.base_model.schedule import Schedule
from src.base_model.appointment import Appointment
from src.base_model.compatibility_checks import check_case_judge_compatibility, check_case_room_compatibility, check_judge_room_compatibility
from src.local_search.move import Move, do_move, undo_move


def calculate_score(schedule: Schedule, move: Move, initial_calculation = False, print_summary=False) -> int:
    """
    Calculate overall score by applying all scoring rules
    OR just the change (delta) in score that a certain move will imply, if a move is provided
    
    Args:
        schedule: The schedule to evaluate
        move: The move being applied, used for delta calculation
        initial_calculation: Whether this is the first time the score is calculated
        print_summary: If True, prints a detailed summary of scores
        
    Returns:
        Total score as an integer
    """
    score = 0
    rule_scores = {}
    
        
    # Apply each rule
    rules = [
        room_stability_per_day,
        case_planned_longer_than_day,
        overbooked_room_in_timeslot,
        overbooked_judge_in_timeslot,
        judge_case_compatibility,
        judge_room_compatiblity,
        case_room_compatibility,
        unused_timeslots,
        schedule_length
    ]
    
    # Apply each rule and accumulate score
    for rule_method in rules:
        rule_name = rule_method.__name__
        rule_score = rule_method(schedule, move, initial_calculation)
        rule_scores[rule_name] = rule_score
        score += rule_score
        
        if print_summary:
            print(f"Rule: {rule_name} - Score: {rule_score}")
    
    if print_summary:
        print("\n=== SCORE SUMMARY ===")
        
        hard_constraints = [
            "overbooked_room_in_timeslot",
            "overbooked_judge_in_timeslot",
            "judge_case_compatibility",
            "judge_room_compatiblity",
            "case_room_compatibility"
        ]
        
        soft_constraints = [
            "room_stability_per_day",
            "case_planned_longer_than_day",
            "unused_timeslots"
        ]
        
        print("\nHard Constraints:")
        hard_total = sum(rule_scores[rule] for rule in hard_constraints)
        for rule in hard_constraints:
            print(f"  {rule}: {rule_scores[rule]}")
        print(f"  Total Hard Constraints: {hard_total}")
        
        print("\nSoft Constraints:")
        soft_total = sum(rule_scores[rule] for rule in soft_constraints)
        for rule in soft_constraints:
            print(f"  {rule}: {rule_scores[rule]}")
        print(f"  Total Soft Constraints: {soft_total}")
        
        print(f"\nTOTAL SCORE: {score}")
        print("==================\n")
    
    return score

def print_score_summary(schedule: Schedule) -> None:
    '''
    Just a wrapper function. Calls calculate_score with print_summary=True.
    This really just exists for code readability.
    '''
    calculate_score(schedule, move=None, print_summary=True)


def room_stability_per_day(schedule: Schedule, move: Move, initial_calculation) -> int:
    """
    Check how many times judges change rooms per day.
    Returns a negative score (-10 points per room change).
    """
    # Full calculation path
    if initial_calculation:
        score = 0
        
        by_day_judge = defaultdict(list)
        for app in schedule.appointments:
            key = ((app.day - 1), app.judge.judge_id)
            by_day_judge[key].append(app)
        
        for (day, judge_id), apps in by_day_judge.items():
            apps.sort(key=lambda a: a.timeslot_in_day)
            
            current_room = None
            for app in apps:
                if current_room is not None and app.room.room_id != current_room:
                    score += 1
                current_room = app.room.room_id
        
        return score
    
    # Delta calculation path
    elif move is not None and (move.new_room is not None or move.new_judge is not None or move.new_day is not None): # Timeslot change won't ever affect total day-wise room stability! (im 98% sure. worked it out on paper)
        affected_judge = move.new_judge.judge_id if move.new_judge else move.appointments[0].judge.judge_id
        affected_day = move.new_day if move.new_day is not None else move.appointments[0].day
        
        old_changes = count_room_changes(schedule, affected_judge, affected_day)
        
        was_applied = move.is_applied
        if not was_applied:
            do_move(move)
        
        new_changes = count_room_changes(schedule, affected_judge, affected_day)
        
        if not was_applied:
            undo_move(move)
        
        return new_changes - old_changes
    
    return 0

def count_room_changes(schedule: Schedule, judge_id: int, day: int) -> int:
    """Helper to count room changes for a judge on a specific day"""
    changes = 0
    
    apps = [app for app in schedule.appointments 
           if app.judge.judge_id == judge_id and app.day == day]
    
    apps.sort(key=lambda a: a.timeslot_in_day)
    
    current_room = None
    for app in apps:
        if current_room is not None and app.room.room_id != current_room:
            changes += 1
        current_room = app.room.room_id
    
    return changes
    

def unused_timeslots(schedule: Schedule, move: Move, initial_calculation: bool) -> int:
    """
    Counts the number of unused timeblocks in the schedule.
    Only calculates delta when the move affects the latest timeslot.
    """
    # Full calculation path
    if initial_calculation:
        # Get all judges
        appointment_judge_ids = set(app.judge.judge_id for app in schedule.appointments)
        max_judge_id = max(appointment_judge_ids) if appointment_judge_ids else 0
        all_judge_ids = set(range(1, max_judge_id + 1))
        
        # Find latest global timeslot
        latest_global_timeslot = 0
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
        move_contains_latest = any(app.case.case_id == latest_app.case.case_id for app in move.appointments)
        
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
                    if any(a.case.case_id == app.case.case_id for a in move.appointments):
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
        case_timeslots = defaultdict(set)
        for app in schedule.appointments:
            case_timeslots[app.case.case_id].add(app.timeslot_in_day)
        
        # Check each case
        for case_id, timeslots in case_timeslots.items():
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
            
            if not check_case_judge_compatibility(app.case.case_id, app.judge.judge_id):
                penalties["judge_case_compatibility"] = 1000
                
            if not check_judge_room_compatibility(app.judge.judge_id, app.room.room_id):
                penalties["judge_room_compatiblity"] = 1000
                
            if not check_case_room_compatibility(app.case.case_id, app.room.room_id):
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
                if not check_case_judge_compatibility(app.case.case_id, move.new_judge.judge_id):
                    penalties["judge_case_compatibility"] = 1000
                    break
            
            for app in move.appointments:
                room_id = move.new_room.room_id if move.new_room else app.room.room_id
                if not check_judge_room_compatibility(move.new_judge.judge_id, room_id):
                    penalties["judge_room_compatiblity"] = 1000
                    break
        
        if move.new_room:
            for app in move.appointments:
                if not check_case_room_compatibility(app.case.case_id, move.new_room.room_id):
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
                                    a.case.case_id != move.case_id)
                if room_conflicts > 0:
                    penalties["overbooked_room_in_timeslot"] += 1000
            
            if move.new_judge and not move.is_applied:
                judge_conflicts = sum(1 for a in schedule.appointments 
                                        if a.day == day and a.timeslot_in_day == timeslot and 
                                        a.judge.judge_id == move.new_judge.judge_id and
                                        a.case.case_id != move.case_id)
                if judge_conflicts > 0:
                    penalties["overbooked_judge_in_timeslot"] += 1000
    
    return penalties