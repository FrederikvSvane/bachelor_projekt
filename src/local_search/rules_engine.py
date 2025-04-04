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
    
    for day in range(1, schedule.work_days + 1):
        if day in schedule.appointments_by_day:
            for timeslot in range(1, schedule.timeslots_per_work_day + 1):
                if timeslot in schedule.appointments_by_day[day]:
                    violations += count_room_overbooking_for_day_timeslot(schedule, day, timeslot)
    
    return (offset + step * violations)
        

def nr1_overbooked_room_in_timeslot_delta(schedule: Schedule, move: Move):
    """
    Tjekker om et rum er overbooket i et givent timeslot.
    """
    
    if move.new_room is None and move.new_day is None and move.new_start_timeslot is None:
        return 0
    
    offset = 0
    step = 1
    
    affected_pairs = get_affected_day_timeslot_pairs_for_overbookings(schedule, move)
    
    violations_before = 0
    for day, timeslot in affected_pairs:
        violations_before += count_room_overbooking_for_day_timeslot(schedule, day, timeslot)
    
    do_move(move, schedule)
    
    violations_after = 0
    for day, timeslot in affected_pairs:
        violations_after += count_room_overbooking_for_day_timeslot(schedule, day, timeslot)
    
    undo_move(move, schedule)
    
    return (offset + step * (violations_after - violations_before))

def nr2_overbooked_judge_in_timeslot_full(schedule: Schedule):
    offset = 0
    step = 1
    violations = 0
    
    for day in range(1, schedule.work_days + 1):
        if day in schedule.appointments_by_day:
            for timeslot in range(1, schedule.timeslots_per_work_day + 1):
                if timeslot in schedule.appointments_by_day[day]:
                    violations += count_judge_overbooking_for_day_timeslot(schedule, day, timeslot)
    
    return (offset + step * violations)

def nr2_overbooked_judge_in_timeslot_delta(schedule: Schedule, move: Move):
    if move.new_judge is None and move.new_day is None and move.new_start_timeslot is None:
        return 0
    
    offset = 0
    step = 1
    
    affected_pairs = get_affected_day_timeslot_pairs_for_overbookings(schedule, move)
    
    violations_before = 0
    for day, timeslot in affected_pairs:
        violations_before += count_judge_overbooking_for_day_timeslot(schedule, day, timeslot)
    
    do_move(move, schedule)
    
    violations_after = 0
    for day, timeslot in affected_pairs:
        violations_after += count_judge_overbooking_for_day_timeslot(schedule, day, timeslot)
    
    undo_move(move, schedule)
    
    return (offset + step * (violations_after - violations_before))
    

def nr6_virtual_room_must_have_virtual_meeting_full(schedule: Schedule):
    offset = 0
    step = 1
    violations = 0
    
    for app in schedule.iter_appointments():
        meeting = app.meeting
        room = app.room
        if not check_case_room_compatibility(meeting.case.case_id, room.room_id):
            violations += 1

    return (offset + step*violations)        

def nr6_virtual_room_must_have_virtual_meeting_delta(schedule: Schedule, move: Move):
    if move.new_room is None:
        return 0
    
    offset = 0
    step = 1
    
    meeting = move.appointments[0].meeting
    
    old_room_has_compatibility = check_case_room_compatibility(meeting.case.case_id, move.old_room.room_id)
    new_room_has_compatibility = check_case_room_compatibility(meeting.case.case_id, move.new_room.room_id)
    
    if old_room_has_compatibility and not new_room_has_compatibility:
        return (offset + step)
    elif not old_room_has_compatibility and new_room_has_compatibility:
        return (offset - step)
    else:
        return 0

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
    
    case_id = move.appointments[0].meeting.case.case_id
    
    old_judge_has_skills = check_case_judge_compatibility(case_id, move.old_judge.judge_id)
    new_judge_has_skills = check_case_judge_compatibility(case_id, move.new_judge.judge_id)
    
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
    violations = 0
    
    for app in schedule.iter_appointments():
        meeting = app.meeting
        judge = app.judge
        if not check_case_judge_compatibility(meeting.case.case_id, judge.judge_id):
            violations += 1
    
    return (offset + step*violations)

def nr14_virtual_case_has_virtual_judge_delta(schedule: Schedule, move: Move):
    if move.new_judge is None:
        return 0
    # NOTE this is actually slower, but more correct. We leave it out.
    # if move.appointments[0].case.characteristics.contains("virtual"):
    #     return 0
    
    offset = 0
    step = 1
    
    case_id = move.appointments[0].meeting.case.case_id
    
    old_judge_is_virtual = check_case_judge_compatibility(case_id, move.old_judge.judge_id)
    new_room_case_compatible = check_case_judge_compatibility(case_id, move.new_judge.judge_id)

    if old_judge_is_virtual and not new_room_case_compatible:    
        return (offset + step)
    elif not old_judge_is_virtual and new_room_case_compatible:
        return (offset - step)
    else:
        return 0

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
    
    judges = schedule.get_all_judges()
    last_day = schedule.work_days
    total_violations = 0
    
    judges_with_appointments_on_last_day = set()
    if last_day in schedule.appointments_by_day:
        for timeslot in schedule.appointments_by_day[last_day]:
            for app in schedule.appointments_by_day[last_day][timeslot]:
                judges_with_appointments_on_last_day.add(app.judge.judge_id)
    
    for day in range(1, last_day + 1):
        for judge in judges:
            judge_id = judge.judge_id
            
            if day == last_day and judge_id not in judges_with_appointments_on_last_day:
                continue
            
            used_timeslots = set()
            if day in schedule.appointments_by_day:
                for timeslot in range(1, schedule.timeslots_per_work_day + 1):
                    if timeslot in schedule.appointments_by_day[day]:
                        for app in schedule.appointments_by_day[day][timeslot]:
                            if app.judge.judge_id == judge_id:
                                used_timeslots.add(timeslot)
                                break  # fandt et appointment i det her timeslot, ingen grund til at lede videre
            
            total_violations += schedule.timeslots_per_work_day - len(used_timeslots)
    
    return (offset + step * total_violations)


def nr18_unused_timegrain_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    
    if move.new_day is None and move.new_judge is None and move.new_start_timeslot is None:
        return 0 
    
    affected_pairs = get_affected_judge_day_pairs_for_unused_timegrains(schedule, move)
    before_violations = calculate_unused_timeslots_for_all_judge_day_pairs(schedule, affected_pairs, schedule.work_days)
    
    do_move(move, schedule)
    
    new_last_day = schedule.work_days
    if new_last_day > schedule.work_days:
        for judge in schedule.get_all_judges():
            affected_pairs.add((new_last_day, judge.judge_id))
    
    after_violations = calculate_unused_timeslots_for_all_judge_day_pairs(schedule, affected_pairs, new_last_day)
    
    undo_move(move, schedule)
    
    return (offset + step * (after_violations - before_violations))

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
    
    day_judge_pairs = set()
    for appointment in schedule.iter_appointments():
        day_judge_pairs.add((appointment.day, appointment.judge.judge_id))
    
    for day, judge_id in day_judge_pairs:
        violations += count_room_changes_for_day_judge_pair(schedule, day, judge_id)
    
    return (offset + step * violations)
                

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