from collections import defaultdict
from typing import Dict

from src.data_generator import ensure_jc_pair_room_compatibility
from src.model import Case, Judge, Room, Attribute, Appointment
from src.graph import UndirectedGraph, DirectedGraph, CaseJudgeRoomNode, CaseJudgeNode, construct_conflict_graph

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
        case_planned_over_night
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
    return 0

def overbooked_judge_in_timeslot(schedule: Schedule) -> int:
    return 0

def overbooked_case_in_timeslot(schedule: Schedule) -> int:
    return 0

def judge_case_room_compatibility(schedule: Schedule) -> int:
    return 0

def virtual_case_must_have_virtual_judge(schedule: Schedule) -> int:
    return 0




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
                score -= 1  # Penalty of -10 per change
                
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
    print(f"Room changes: {len(room_changes)} detected (-10 points each)")
    
    return score

def case_planned_over_night(schedule: Schedule) -> int:
    """
    Check if a case is planned both at the end of day x and start of day y.
    """
    score = 0
    for app in schedule.appointments:
        if app.timeslot_start + app.timeslots_duration > schedule.timeslots_per_work_day:
            # Case is planned over night
            score -= 10
    return score