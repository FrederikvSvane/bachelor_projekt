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
    
    
    appointments = schedule.get_all_appointments()
    for appointment in appointments:
        room = appointment.room
        day = appointment.day
        room_key = (room.room_id, day, appointment.timeslot_in_day)
        if room_key in room_usage:
            room_usage[room_key] += 1
        else:
            room_usage[room_key] = 1

    for count in room_usage.values():
            if count > 1:
                #print(f"Day: {day}, timeslot: {appointment.timeslot_in_day}, room: {room.room_id}")
                violations += 1

    return (offset + step*violations)
        

def nr1_overbooked_room_in_timeslot_delta(schedule: Schedule, move: Move):
    """
    Tjekker om et rum er overbooket i et givent timeslot.
    """
    
    if move.new_room is None and move.new_day is None and move.new_start_timeslot is None:
        return 0
    
    offset = 0
    step = 1
    old_violations = 0
    
    for app in move.appointments:
        appointments_at_time = schedule.appointments_by_day[app.day][app.timeslot_in_day]
        room_ids = [app.room.room_id for app in appointments_at_time]
        double_booked = len(room_ids) != len(set(room_ids))
        if double_booked:
            old_violations += 1
    
    do_move(move, schedule)
    
    new_violations = 0
    for app in move.appointments:
        appointments_at_time = schedule.appointments_by_day[app.day][app.timeslot_in_day]
        room_ids = [app.room.room_id for app in appointments_at_time]
        double_booked = len(room_ids) != len(set(room_ids))
        if double_booked:
            new_violations += 1
    
    undo_move(move, schedule)
    
    #print(f"violations before: {old_violations}, violations after: {new_violations}")
    #print(f"returning: {new_violations - old_violations}")

    
    return (offset + step*(new_violations - old_violations))

def nr2_overbooked_judge_in_timeslot_full(schedule: Schedule):
    offset = 0
    step = 1
    
    violations = 0
    judge_usage = {}

    appointments = schedule.get_all_appointments()
    for appointment in appointments:
        judge = appointment.judge
        day = appointment.day
        judge_key = (judge.judge_id, day, appointment.timeslot_in_day)
        if judge_key in judge_usage:
            judge_usage[judge_key] += 1
        else:
            judge_usage[judge_key] = 1
    
    for count in judge_usage.values():
        if count > 1:
            violations += 1
    
    return (offset + step*violations)

def nr2_overbooked_judge_in_timeslot_delta(schedule: Schedule, move: Move):
    
    if move.new_judge is None and move.new_day is None and move.new_start_timeslot is None:
        return 0

    offset = 0
    step = 1
    old_violations = 0
    
    for app in move.appointments:
        appointments_at_time = schedule.appointments_by_day[app.day][app.timeslot_in_day]
        judge_ids = [app.judge.judge_id for app in appointments_at_time]
        double_booked = len(judge_ids) != len(set(judge_ids))
        if double_booked:
            old_violations += 1
    
    do_move(move, schedule)
    
    new_violations = 0
    for app in move.appointments:
        appointments_at_time = schedule.appointments_by_day[app.day][app.timeslot_in_day]
        judge_ids = [app.judge.judge_id for app in appointments_at_time]
        double_booked = len(judge_ids) != len(set(judge_ids))
        if double_booked:
            new_violations += 1
    
    undo_move(move, schedule)
    #print(f"violations before: {old_violations}, violations after: {new_violations}")
    #print(f"returning: {new_violations - old_violations}")
    
    return (offset + step*(new_violations - old_violations))
    
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
    for appointment in schedule.iter_appointments():
        judge = appointment.judge
        case = appointment.meeting.case
        if not check_case_judge_compatibility(case, judge):
            violations += 1
    
    return (offset + step*violations)

def nr8_judge_skillmatch_delta(_: Schedule, move: Move):
    if move.new_judge is None:
        return 0
    
    offset = 0
    step = 1
    
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

def nr14_virtual_case_has_virtual_judge_full(schedule: Schedule):
    offset = 0
    step = 1
    pass

def nr14_virtual_case_has_virtual_judge_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass

# ...

def nr17_unused_timeblock_full(schedule: Schedule):
    offset = 0
    step = 1
    pass

def nr17_unused_timeblock_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass

def nr18_unused_timegrain_full(schedule: Schedule):
    offset = 0
    step = 1
    
    all_judge_ids = schedule.get_all_judges()
    used_global_slots = set()
    latest_global_timeslot = get_latest_global_timeslot(schedule)
    
    for app in schedule.iter_appointments():
        judge_id = app.judge.judge_id
        global_timeslot = (app.day - 1) * schedule.timeslots_per_work_day + app.timeslot_in_day
        used_global_slots.add((judge_id, global_timeslot))
    
    total_possible_slots = len(all_judge_ids) * latest_global_timeslot
    
    violations = total_possible_slots - len(used_global_slots)
    return (offset + step*violations)


def nr18_unused_timegrain_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    
    if (move.new_day is None and move.new_judge is None and move.new_start_timeslot is None and move.new_room is None):
        return 0
    
    meeting_moved_in_time = move.new_day is not None or move.new_start_timeslot is not None

    if not meeting_moved_in_time:
        return 0

    if move.new_start_timeslot is None: 
        return 0
    
    get_latest_global_timeslot = get_latest_global_timeslot(schedule)


    # TODO
    # we need to find the distance between the latest global timeslot and the second latest global timeslot
    # then do something smart

    # TODO
    # but in the normal case were we are not at the boundary of the schedule, we can just do something like
    # look at the slice in the schedule that is affected by the move
    # and if it is moved in time, then consider the slice in time before and after the move




    pass


    return (offset + step * delta)

def nr19_case_has_specific_judge_full(schedule: Schedule):
    offset = 0
    step = 1
    pass

def nr19_case_has_specific_judge_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass

def nr20_max_weekly_coverage_full(schedule: Schedule):
    offset = 0
    step = 1
    pass

def nr20_max_weekly_coverage_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass

def nr21_all_meetings_planned_for_case_full(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass

def nr21_all_meetings_planned_for_case_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass

def nr22_case_meetings_too_sparsely_planned_full(schedule: Schedule):
    offset = 0
    step = 1
    pass

def nr22_case_meetings_too_sparsely_planned_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass

# ...

def nr25_room_missing_video_full(schedule: Schedule):
    offset = 0
    step = 1
    pass

def nr25_room_missing_video_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass

def nr26_room_missing_optional_entry_full(schedule: Schedule):
    offset = 0
    step = 1
    pass

def nr26_room_missing_optional_entry_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass

def nr27_overdue_case_not_planned_full(schedule: Schedule):
    offset = 0
    step = 1
    pass

def nr27_overdue_case_not_planned_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass

def nr28_overdue_case_full(schedule: Schedule):
    offset = 0
    step = 1
    pass

def nr28_overdue_case_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass

def nr29_room_stability_per_day_full(schedule: Schedule):
    offset = 0
    step = 1
    
    violations = 0

    appointments = schedule.get_all_appointments()
    
    apps_pr_judge_pr_day = {}
    for appointment in appointments:
        key = (appointment.day, appointment.judge.judge_id)
        if key not in apps_pr_judge_pr_day:
            apps_pr_judge_pr_day[key] = []
        apps_pr_judge_pr_day[key].append(appointment)
    
    for (day, judge_id), appointments in apps_pr_judge_pr_day.items():
        appointments.sort(key=lambda a: (a.timeslot_in_day, a.meeting.meeting_id))
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
    do_move(move, schedule)

    violations_after = 0
    for day, judge_id in affected_day_judge_pairs:
        violations_after += count_room_changes_for_day_judge_pair(schedule, day, judge_id)
        
    undo_move(move, schedule)

    return (offset + step*(violations_after - violations_before))

def nr30_schedule_length_full(schedule: Schedule):
    offset = 0
    step = 1
    pass

def nr30_schedule_length_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass