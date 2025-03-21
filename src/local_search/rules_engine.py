from collections import defaultdict
from src.base_model.schedule import Schedule
from src.base_model.appointment import Appointment
from src.base_model.compatibility_checks import check_case_judge_compatibility, check_case_room_compatibility, check_judge_room_compatibility
from src.local_search.move import Move


def calculate_score(schedule: Schedule, move: Move, initial_calculation = False, print_summary=False) -> int:
    """
    Calculate overall score by applying all scoring rules
    
    Args:
        schedule: The schedule to evaluate
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
    
    # Print a summary if requested
    if print_summary:
        print("\n=== SCORE SUMMARY ===")
        
        # Group by constraint type
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
    """
    Convenience function to print a summary of the schedule's score
    """
    calculate_score(schedule, print_summary=True)
    
##########################################################
############## RULES DEFINED AS FUNCTIONS ################
##########################################################

##########################################################
############## HARD CONSTRAINTS ##########################
##########################################################
def overbooked_room_in_timeslot(schedule: Schedule, move, initial_calculation) -> int:
        return check_hard_constraints(schedule, move, initial_calculation)["overbooked_room_in_timeslot"]

def overbooked_judge_in_timeslot(schedule: Schedule, move, initial_calculation) -> int:
    return check_hard_constraints(schedule, move, initial_calculation)["overbooked_judge_in_timeslot"]

def judge_case_compatibility(schedule: Schedule, move, initial_calculation) -> int:
    return check_hard_constraints(schedule, move, initial_calculation)["judge_case_compatibility"]

def judge_room_compatiblity(schedule: Schedule, move, initial_calculation) -> int:
    return check_hard_constraints(schedule, move, initial_calculation)["judge_room_compatiblity"]

def case_room_compatibility(schedule: Schedule, move, initial_calculation) -> int:
    return check_hard_constraints(schedule, move, initial_calculation)["case_room_compatibility"]


##########################################################
############## SOFT CONSTRAINTS ##########################
##########################################################
def room_stability_per_day(schedule: Schedule, move, initial_calculation) -> int:
    """
    Check how many times judges change rooms per day.
    Returns a negative score (-10 points per room change).
    """
    score = 0
    room_changes = []
    
    # Group appointments by day and judge
    by_day_judge = defaultdict(list)
    for app in schedule.appointments:
        key = ((app.day - 1)  , app.judge.judge_id)
        by_day_judge[key].append(app)
    
    # For each day and judge, check for room changes
    for (day, judge_id), apps in by_day_judge.items():
        # Sort by timeslot to get chronological order
        apps.sort(key=lambda a: a.timeslot_in_day)
        
        # Track room changes
        current_room = None
        for app in apps:
            if current_room is not None and app.room.room_id != current_room:
                # Room change detected
                score += 1
                
                # Record the change
                room_changes.append({
                    "day": day,
                    "judge_id": judge_id,
                    "from_room": current_room,
                    "to_room": app.room.room_id,
                    "timeslot": app.timeslot_in_day
                })
            
            # Update current room
            current_room = app.room.room_id
    # Print summary
    #print(f"Room changes: {len(room_changes)} detected (+1 points each)")
    
    return score

def unused_timeslots(schedule: Schedule, move: Move, initial_calculation: bool) -> int:
    """
    Counts the number of unused timeblocks in the schedule.
    Counts up to the latest meeting by any judge globally.
    Handles judges with no appointments.
    """
    # We need to know all judges, not just those with appointments
    # Determine the number of judges from the highest judge ID
    if move.new_start_timeslot or initial_calculation:
        appointment_judge_ids = set(app.judge.judge_id for app in schedule.appointments)
        max_judge_id = max(appointment_judge_ids) if appointment_judge_ids else 0
        
        # Create a complete set of judge IDs (assuming sequential IDs starting from 1)
        all_judge_ids = set(range(1, max_judge_id + 1))
        
        # Track used timeslots for each (judge, timeslot)
        used_global_slots = set()
        
        # Find the global latest timeslot (across all judges)
        latest_global_timeslot = 0
        
        for app in schedule.appointments:
            judge_id = app.judge.judge_id
            # Calculate global timeslot
            global_timeslot = (app.day - 1) * schedule.timeslots_per_work_day + app.timeslot_in_day
            used_global_slots.add((judge_id, global_timeslot))
            
            # Update the global latest timeslot
            latest_global_timeslot = max(latest_global_timeslot, global_timeslot)
        
        # Calculate unused slots
        unused_slots = 0
        
        # For each judge, count unused slots up to the global latest appointment
        for judge_id in all_judge_ids:
            for global_timeslot in range(1, latest_global_timeslot + 1):
                if (judge_id, global_timeslot) not in used_global_slots:
                    unused_slots += 1
                    
    
        return unused_slots
    return 0

def schedule_length(schedule: Schedule, move: Move, initial_calculation: bool) -> int:
    """
    Calculate the total length of the schedule in minutes.
    """
    # Find the latest timeslot of any appointment
    if move.new_start_timeslot or initial_calculation:
        return max(schedule.timeslots_per_work_day * (app.day-1) + app.timeslot_in_day for app in schedule.appointments if isinstance(app, Appointment))
    return 0

def case_planned_longer_than_day(schedule: Schedule, move: Move, initial_calculation) -> int: 
    """
    Check if a case is planned both at the end of day x and start of day y.
    Apply penalty only once per case.
    """
    if move.new_start_timeslot or initial_calculation:
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

##########################################################
############## HELPER FUNCTIONS ##########################
##########################################################

def check_hard_constraints(schedule: Schedule, move: Move, initial_calculation) -> dict:
    """
    Efficiently checks all hard scheduling constraints in a single pass
    Returns a dictionary with penalties for each constraint
    """
    # Initialize penalties
    penalties = {
        "overbooked_room_in_timeslot": 0,
        "overbooked_judge_in_timeslot": 0,
        "judge_case_compatibility": 0,
        "judge_room_compatiblity": 0,
        "case_room_compatibility": 0
    }
    
    # Create tracking dictionaries
    room_usage = {}  # (room_id, timeslot) -> count
    judge_usage = {}  # (judge_id, timeslot) -> count
    
    # Check all constraints in a single pass
    for app in schedule.appointments:
        # Check resource overbooking
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
        
        # Check compatibility constraints
        if move.new_judge or initial_calculation:
            if not check_case_judge_compatibility(app.case.case_id, app.judge.judge_id):
                penalties["judge_case_compatibility"] = 1000
            
        if move.new_room or move.new_judge or initial_calculation:
            if not check_judge_room_compatibility(app.judge.judge_id, app.room.room_id):
                penalties["judge_room_compatiblity"] = 1000
            
        if move.new_room or initial_calculation:
            if not check_case_room_compatibility(app.case.case_id, app.room.room_id):
                penalties["case_room_compatibility"] = 1000
    
    # Calculate overbooking penalties
    for count in room_usage.values():
        if count > 1:
            penalties["overbooked_room_in_timeslot"] += 1000 * (count - 1)
            
    for count in judge_usage.values():
        if count > 1:
            penalties["overbooked_judge_in_timeslot"] += 1000 * (count - 1)
            break
    
    return penalties


def print_score_summary(schedule: Schedule) -> None:
    calculate_score(schedule, print_summary=True)