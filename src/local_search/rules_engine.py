from collections import defaultdict
from sys import exit

from src.base_model.schedule import Schedule
from src.base_model.appointment import Appointment
from src.base_model.compatibility_checks import check_case_judge_compatibility, check_case_room_compatibility, check_judge_room_compatibility
from src.local_search.move import Move, do_move, undo_move
from src.local_search.rules_engine_helpers import *


# 2 ooms scale difference per category
hard_containt_weight = 10,000,000
medm_containt_weight = 100,000
soft_containt_weight = 1,000

def calculate_full_score(schedule: Schedule) -> int:
    
    # Hard
    hard_violations = 0
    hard_violations += nr8_judge_skillmatch_full(schedule)
    
    
    # Medium
    medm_violations = 0
    # nr17_unusedtimeblock
    # nr18_unusedtimegrain
    
    # Soft
    soft_violations = 0
    soft_violations += nr29_room_stability_per_day_full(schedule)

    score = hard_violations*hard_containt_weight + medm_violations*medm_containt_weight + soft_violations*soft_containt_weight        
    return score

def calculate_delta_score(schedule: Schedule, move: Move) -> int:
    """
    do the move AFTER calling this function.
    NOT BEFORE!!!
    """
    if move is None or move.old_judge is None or move.old_room is None or move.old_start_timeslot is None or move.old_day is None:
        print("cant work with this move. set the old values to something that isnt None")
        exit()
    if move.is_applied:
        print("nope. read the function description")
        exit()
    
    # Hard rules
    hard_violations = 0
    
    violations += nr29_room_stability_per_day_delta(schedule, move)
    
    return 0



def nr1_overbooked_room_in_timeslot_full(schedule: Schedule):
    """
    Tjekker hvor mange gange et rum er booket i et givent timeslot.
    """
    offset = 0
    step = 1
    violations = 0
    room_usage =  {}

    for appointment in schedule.appointments:
        room = appointment.room
        day = appointment.day
        room_key = (room.room_id, day, appointment.timeslot_in_day)
        if room_key in room_usage:
            room_usage[room_key] += 1
        else:
            room_usage[room_key] = 1

    for count in room_usage.values():
            if count > 1:
                violations += 1

    return (offset + step*violations)
        

def nr1_overbooked_room_in_timeslot_delta(schedule: Schedule, move: Move):
    """
    Tjekker om et rum er overbooket i et givent timeslot.
    """
    
    if move.new_room is None:
        return 0
    
    offset = 0
    step = 1
    

    old_appointments_in_time_range = get_all_appointments_starting_from_timeslot(schedule, move.old_day, move.old_start_timeslot)
    room_usage = {}
    # First check the entire span of the meeting for the old room and check if it is overbooked
    meeting = move.appointments[0].meeting
    old_room_key = (move.old_room.room_id, move.old_day, move.old_start_timeslot)
    old_room_usage = 0
    
    
    # Then check the entire span of the meeting for the new room and check if it is overbooked
    
    

    new_room_key = (move.new_room.room_id, move.new_day, move.new_start_timeslot)
    





    
    violations = 0
    


    pass

def nr2_overbooked_judge_in_timeslot_full(schedule: Schedule):
    offset = 0
    step = 1
    pass

def nr2_overbooked_judge_in_timeslot_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass

# ...

def nr6_virtual_room_must_have_virtual_meeting_full(schedule: Schedule):
    offset = 0
    step = 1
    pass

def nr6_virtual_room_must_have_virtual_meeting_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass

# ...

def nr8_judge_skillmatch_full(schedule: Schedule):
    """
    Tjekker om dommeren har de nødvendige skills til at dømme en sag.
    En violation bliver tilføjet for hver appointmnent, hvor dommeren ikke har de nødvendige skills.
    """
    offset = 0
    step = 1
    
    violations = 0
    for appointment in schedule.appointments:
        judge = appointment.judge
        case = appointment.meeting.case
        if not check_case_judge_compatibility(case, judge):
            violations += 1
    
    return (offset + step*violations)

def nr8_judge_skillmatch_delta(schedule: Schedule, move: Move):
    if move.new_judge is None:
        return 0
    
    offset = 0
    step = 1
    
    # this could follow the pattern:
    # 1. get affected appointments
    # 2. calculate violations before move
    # 3. do move
    # 4. calculate violations after move
    # 5. undo move
    # 6. return (offset + step*(violations_after - violations_before))
    
    # but since theres only going to be one affected meeting always, we can just do this:
    
    meeting = move.appointments[0].meeting
    
    old_judge_has_skills = check_case_judge_compatibility(move.old_judge, meeting)
    new_judge_has_skills = check_case_judge_compatibility(move.new_judge, meeting)
    
    if old_judge_has_skills and not new_judge_has_skills:
        return (offset + step)
    elif not old_judge_has_skills and new_judge_has_skills:
        return (offset - step)
    else:
        return 0

# ...

def nr20_max_weekly_coverage_full(schedule: Schedule):
    offset = 0
    step = 1
    pass

def nr20_max_weekly_coverage_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass

# ...

def nr29_room_stability_per_day_full(schedule: Schedule):
    offset = 0
    step = 1
    
    violations = 0
    
    apps_pr_judge_pr_day = {}
    for appointment in schedule.appointments:
        key = (appointment.day, appointment.judge.judge_id)
        if key not in apps_pr_judge_pr_day:
            apps_pr_judge_pr_day[key] = []
        apps_pr_judge_pr_day[key].append(appointment)
    
    for (day, judge_id), appointments in apps_pr_judge_pr_day.items():
        appointments.sort(key=lambda a: a.timeslot_in_day)
        
        current_room_id = None
        for appointment in appointments:
            if current_room_id is not None and appointment.room.room_id != current_room_id:
                violations += 1
            current_room_id = appointment.room.room_id
    
    return (offset + step*violations)
                

def nr29_room_stability_per_day_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    
    if (move.new_day is None and move.new_judge is None and move.new_start_timeslot is None and move.new_room is None):
        return 0 # probably wont ever happen, but fine to have for future delete moves i guess

    affected_day_judge_pairs = get_affected_pairs_for_room_stability(schedule, move)
    
    violations_before = 0
    for day, judge_id in affected_day_judge_pairs:
        violations_before += count_room_changes_for_day_judge_pair(schedule, day, judge_id)
    
    do_move(move)
    
    violations_after = 0
    for day, judge_id in affected_day_judge_pairs:
        violations_after += count_room_changes_for_day_judge_pair(schedule, day, judge_id)
        
    undo_move(move)
    
    return (offset + step*(violations_after - violations_before))