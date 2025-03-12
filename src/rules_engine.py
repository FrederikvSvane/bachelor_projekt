from collections import defaultdict
from typing import Dict

from src.data_generator import ensure_jc_pair_room_compatibility
from src.model import Case, Judge, Room, Attribute, Appointment
from src.graph import UndirectedGraph, DirectedGraph, CaseJudgeRoomNode, CaseJudgeNode, construct_conflict_graph, case_judge_compatible, judge_room_compatible, case_room_compatible

from src.matching import (
    assign_cases_to_judges, assign_case_judge_pairs_to_rooms, 
)
from src.coloring import DSatur
from src.graph import UndirectedGraph, DirectedGraph, CaseJudgeRoomNode
from src.model import Appointment
from src.schedule import Schedule
      
def calculate_score(schedule: Schedule) -> int:
    """Calculate overall score by applying all scoring rules"""
    score = 0
    
    # Apply each rule
    rules = [
        room_stability_per_day,
        case_planned_longer_than_day,
        overbooked_room_in_timeslot,
        overbooked_judge_in_timeslot,
        judge_case_compatibility,
        judge_room_compatiblity,
        case_room_compatibility,
        unused_timeslots
        # Add other rule functions here
    ]
    
    # Apply each rule and accumulate score
    for rule_method in rules:
        rule_name = rule_method.__name__
        rule_score = rule_method(schedule)  # Pass schedule to the function
        print(f"Rule: {rule_name} - Score: {rule_score}")
        score += rule_score
    
    return score
    
##########################################################
############## RULES DEFINED AS FUNCTIONS ################
##########################################################

##########################################################
############## HARD CONSTRAINTS ##########################
##########################################################
def overbooked_room_in_timeslot(schedule: Schedule) -> int:
    return check_hard_constraints(schedule)["overbooked_room_in_timeslot"]

def overbooked_judge_in_timeslot(schedule: Schedule) -> int:
    return check_hard_constraints(schedule)["overbooked_judge_in_timeslot"]

def judge_case_compatibility(schedule: Schedule) -> int:
    return check_hard_constraints(schedule)["judge_case_compatibility"]

def judge_room_compatiblity(schedule: Schedule) -> int:
    return check_hard_constraints(schedule)["judge_room_compatiblity"]

def case_room_compatibility(schedule: Schedule) -> int:
    return check_hard_constraints(schedule)["case_room_compatibility"]


##########################################################
############## SOFT CONSTRAINTS ##########################
##########################################################
def room_stability_per_day(schedule: Schedule) -> int:
    """
    Check how many times judges change rooms per day.
    Returns a negative score (-10 points per room change).
    """
    score = 0
    room_changes = []
    
    # Group appointments by day and judge
    by_day_judge = defaultdict(list)
    for app in schedule.appointments:
        key = (app.day, app.judge.judge_id)
        by_day_judge[key].append(app)
    
    # For each day and judge, check for room changes
    for (day, judge_id), apps in by_day_judge.items():
        # Sort by timeslot to get chronological order
        apps.sort(key=lambda a: a.timeslot_start)
        
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
                    "timeslot": app.timeslot_start
                })
            
            # Update current room
            current_room = app.room.room_id
    # Print summary
    print(f"Room changes: {len(room_changes)} detected (+1 points each)")
    
    return score

def unused_timeslots(schedule: Schedule) -> int:
    """
    Counts the number of unused timeblocks in the schedule.
    Counts up to the latest meeting by any judge globally.
    Handles judges with no appointments.
    """
    # We need to know all judges, not just those with appointments
    # Determine the number of judges from the highest judge ID
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
        global_timeslot = app.day * schedule.timeslots_per_work_day + (app.timeslot_start % schedule.timeslots_per_work_day)
        used_global_slots.add((judge_id, global_timeslot))
        
        # Update the global latest timeslot
        latest_global_timeslot = max(latest_global_timeslot, global_timeslot)
    
    # Calculate unused slots
    unused_slots = 0
    
    # For each judge, count unused slots up to the global latest appointment
    for judge_id in all_judge_ids:
        for global_timeslot in range(latest_global_timeslot + 1):
            if (judge_id, global_timeslot) not in used_global_slots:
                unused_slots += 1
                
   
    return unused_slots
            

def case_planned_longer_than_day(schedule: Schedule) -> int: 
    """
    Check if a case is planned both at the end of day x and start of day y.
    Apply penalty only once per case.
    """
    score = 0
    
    # Group timeslots by case_id
    case_timeslots = defaultdict(set)
    for app in schedule.appointments:
        case_timeslots[app.case.case_id].add(app.timeslot_start)
    
    # Check each case
    for case_id, timeslots in case_timeslots.items():
        # Check each day boundary
        for day in range(schedule.work_days - 1):
            last_slot_of_day = (day + 1) * schedule.timeslots_per_work_day - 1
            first_slot_of_next_day = (day + 1) * schedule.timeslots_per_work_day
            
            # If case has appointments on both sides of boundary, penalize it
            if last_slot_of_day in timeslots and first_slot_of_next_day in timeslots:
                print(f"Case {case_id} scheduled longer than the day: timeslots {last_slot_of_day} and {first_slot_of_next_day}")
                score += 10
                break  # Only penalize once per case
    
    return score

##########################################################
############## HELPER FUNCTIONS ##########################
##########################################################

def check_hard_constraints(schedule: Schedule) -> dict:
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
        room_key = (app.room.room_id, app.timeslot_start)
        if room_key in room_usage:
            room_usage[room_key] += 1
        else:
            room_usage[room_key] = 1
            
        judge_key = (app.judge.judge_id, app.timeslot_start)
        if judge_key in judge_usage:
            judge_usage[judge_key] += 1
        else:
            judge_usage[judge_key] = 1
        
        # Check compatibility constraints
        if not case_judge_compatible(app.case, app.judge):
            penalties["judge_case_compatibility"] = 1000
            
        if not judge_room_compatible(app.judge, app.room):
            penalties["judge_room_compatiblity"] = 1000
            
        if not case_room_compatible(app.case, app.room):
            penalties["case_room_compatibility"] = 1000
    
    # Calculate overbooking penalties
    for count in room_usage.values():
        if count > 1:
            penalties["overbooked_room_in_timeslot"] += 1000 * (count - 1)
            
    for count in judge_usage.values():
        if count > 1:
            penalties["overbooked_judge_in_timeslot"] = 1000
            break
    
    return penalties