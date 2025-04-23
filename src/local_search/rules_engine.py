from collections import defaultdict

from src.base_model.schedule import Schedule
from src.base_model.appointment import Appointment, print_appointments
from src.base_model.compatibility_checks import check_case_judge_compatibility, check_case_room_compatibility, check_judge_room_compatibility
from src.local_search.move import Move, do_move, undo_move
from src.local_search.rules_engine_helpers import *


# TODO These should be updated based on the size of the problem.
# Even if every single appointment breaks a soft constraint, the penalty from that should be less than a single medium constraint.
# 10 judges * 78 timeslots * 10 days = 7800 potential soft and medium violations => 1, e4, e8 works.
hard_containt_weight = 100_000_000
medm_containt_weight = 10_000
soft_containt_weight = 1

def calculate_full_score(schedule: Schedule) -> int:
    # Hard
    hard_violations = 0
    hard_violations += nr1_overbooked_room_in_timeslot_full(schedule)
    hard_violations += nr2_overbooked_judge_in_timeslot_full(schedule)
    hard_violations += nr6_virtual_room_must_have_virtual_meeting_full(schedule)
    hard_violations += nr8_judge_skillmatch_full(schedule)
    hard_violations += nr14_virtual_case_has_virtual_judge_full(schedule)
    
    # Medium
    medm_violations = 0
    medm_violations += nr18_unused_timegrain_full(schedule)

    # Soft
    soft_violations = 0
    unplanned_meetings = nr27_overdue_case_not_planned_full(schedule)  # Add this line
    soft_violations += unplanned_meetings
    soft_violations += nr29_room_stability_per_day_full(schedule)
    soft_violations += nr31_distance_between_meetings_full(schedule)

    full_score = hard_violations * hard_containt_weight + medm_violations * medm_containt_weight + soft_violations * soft_containt_weight
    
    print(f"FULL: Hard Violations: {hard_violations} unplanned meetings), Medium Violations: {medm_violations}, Soft Violations: {soft_violations}")  
    
    return full_score

def calculate_delta_score(schedule: Schedule, move: Move) -> int:
    """
    do the move AFTER calling this function.
    NOT BEFORE!!!
    """
    if move is None or move.is_applied:
        raise ValueError("Move is None or already applied.")
    
    # Special handling for insertion moves - set dummy "old" values
    # This allows insertion moves to pass the validation check but doesn't affect calculation
    if move.is_insert_move:
        populate_insert_move_appointments(schedule, move)

        if move.appointments is None or len(move.appointments) == 0:
            raise ValueError("Move has no appointments.")
        
    # Hard rules
    hard_violations = 0
    hard_violations += nr1_overbooked_room_in_timeslot_delta(schedule, move)
    hard_violations += nr2_overbooked_judge_in_timeslot_delta(schedule, move)
    hard_violations += nr6_virtual_room_must_have_virtual_meeting_delta(schedule, move)
    hard_violations += nr8_judge_skillmatch_delta(schedule, move)
    hard_violations += nr14_virtual_case_has_virtual_judge_delta(schedule, move)

    # Medium rules
    medm_violations = 0
    medm_violations += nr18_unused_timegrain_delta(schedule, move)

    # Soft rules
    soft_violations = 0  
    soft_violations += nr27_overdue_case_not_planned_delta(schedule, move)  
    soft_violations += nr29_room_stability_per_day_delta(schedule, move)
    soft_violations += nr31_distance_between_meetings_delta(schedule, move)

    delta_score = hard_containt_weight * hard_violations + medm_containt_weight * medm_violations + soft_containt_weight * soft_violations

    print(f"DELTA: Hard Violations: {hard_violations}, Medium Violations: {medm_violations}, Soft Violations: {soft_violations}")

    return delta_score

 
        
def nr1_overbooked_room_in_timeslot_full(schedule: Schedule):
    """
    Tjekker hvor mange gange et rum er booket i et givent timeslot.
    """
    offset = 0
    step = 1
    violations = 0
    
    for day in range(1, schedule.work_days + 1):
        if day in schedule.appointments_by_day_and_timeslot:
            for timeslot in range(1, schedule.timeslots_per_work_day + 1):
                if timeslot in schedule.appointments_by_day_and_timeslot[day]:
                    violations += count_room_overbooking_for_day_timeslot(schedule, day, timeslot)
    
    return (offset + step * violations)
        

def nr1_overbooked_room_in_timeslot_delta(schedule: Schedule, move: Move):
    """
    Tjekker om et rum er overbooket i et givent timeslot.
    """
    
    if not move.is_delete_move and move.new_room is None and move.new_day is None and move.new_start_timeslot is None:
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
        if day in schedule.appointments_by_day_and_timeslot:
            for timeslot in range(1, schedule.timeslots_per_work_day + 1):
                if timeslot in schedule.appointments_by_day_and_timeslot[day]:
                    violations += count_judge_overbooking_for_day_timeslot(schedule, day, timeslot)
    
    return (offset + step * violations)

def nr2_overbooked_judge_in_timeslot_delta(schedule: Schedule, move: Move):
    if not move.is_delete_move and move.new_judge is None and move.new_day is None and move.new_start_timeslot is None:
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
    offset = 0
    step = 1
    
    case_id: int = move.appointments[0].meeting.case.case_id
    
    if move.is_delete_move:
        # only possible violation is if the room and meeting where previously incompatible
        # delete moves will always give no violations
        return 0 if check_case_room_compatibility(case_id, move.old_room.room_id) else -len(move.appointments)
    
    if not move.is_delete_move and move.new_room is None:
        return 0
    
    do_move(move, schedule) 
    
    old_room_has_compatibility = check_case_room_compatibility(case_id, move.old_room.room_id)
    new_room_has_compatibility = check_case_room_compatibility(case_id, move.new_room.room_id)
    
    if old_room_has_compatibility and not new_room_has_compatibility: # was compatible, now incompatible => Adding violations
        violations = len(move.appointments)
    elif not old_room_has_compatibility and new_room_has_compatibility: # was incompatible, now compatible => Removing violations
        violations = -len(move.appointments)
    else:
        violations = 0

    undo_move(move, schedule)
    return (offset + step*violations)

def nr8_judge_skillmatch_full(schedule: Schedule):
    """
    Tjekker om dommeren har de nødvendige skills til at dømme en sag.
    En violation bliver tilføjet for hver appointmnent, hvor dommeren ikke har de nødvendige skills.
    """
    offset = 0
    step = 1
    violations = 0

    for appointment in schedule.iter_appointments():
        meeting = appointment.meeting
        judge = appointment.judge
        if not check_case_judge_compatibility(meeting.case.case_id, judge.judge_id):
            violations += 1
    
    return (offset + step*violations)

def nr8_judge_skillmatch_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    case_id: int = move.appointments[0].meeting.case.case_id
    
    if move.is_delete_move:
        # only possible violation is if the judge and meeting where previously incompatible
        # delete moves will always give no violations
        return 0 if check_case_judge_compatibility(case_id, move.old_judge.judge_id) else -len(move.appointments)
    
    if not move.is_delete_move and move.new_judge is None:
        return 0
    
    do_move(move, schedule)
    
    old_judge_has_skills = check_case_judge_compatibility(case_id, move.old_judge.judge_id)
    new_judge_has_skills = check_case_judge_compatibility(case_id, move.new_judge.judge_id)
    
    if old_judge_has_skills and not new_judge_has_skills: # was compatible, now incompatible => Adding violations
        violations = len(move.appointments)
    elif not old_judge_has_skills and new_judge_has_skills: # was incompatible, now compatible => Removing violations
        violations = -len(move.appointments)
    else:
        violations = 0

    undo_move(move, schedule)
    return (offset + step*violations)

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
    offset = 0
    step = 1
    case_id = move.appointments[0].meeting.case.case_id
    
    if move.is_delete_move:
        # only possible violation is if the judge and meeting where previously incompatible
        # delete moves will always give no violations
        return 0 if check_case_judge_compatibility(case_id, move.old_judge.judge_id) else -len(move.appointments)
    
    if not move.is_delete_move and move.new_judge is None:
        return 0
    # NOTE this is actually slower, but more correct. We leave it out.
    # if move.appointments[0].case.characteristics.contains("virtual"):
    #     return 0
    
    do_move(move, schedule) 
    
    old_judge_is_virtual = check_case_judge_compatibility(case_id, move.old_judge.judge_id)
    new_room_case_compatible = check_case_judge_compatibility(case_id, move.new_judge.judge_id)

    if old_judge_is_virtual and not new_room_case_compatible: # was compatible, now incompatible => Adding violations
        violations = len(move.appointments)
    elif not old_judge_is_virtual and new_room_case_compatible: # was incompatible, now compatible => Removing violations
        violations = -len(move.appointments)
    else:
        violations = 0

    undo_move(move, schedule)
    return (offset + step*violations)

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
    if last_day in schedule.appointments_by_day_and_timeslot:
        for timeslot in schedule.appointments_by_day_and_timeslot[last_day]:
            for app in schedule.appointments_by_day_and_timeslot[last_day][timeslot]:
                judges_with_appointments_on_last_day.add(app.judge.judge_id)
    
    for day in range(1, last_day + 1):
        for judge in judges:
            judge_id = judge.judge_id
            
            if day == last_day and judge_id not in judges_with_appointments_on_last_day:
                continue
            
            used_timeslots = set()
            if day in schedule.appointments_by_day_and_timeslot:
                for timeslot in range(1, schedule.timeslots_per_work_day + 1):
                    if timeslot in schedule.appointments_by_day_and_timeslot[day]:
                        for app in schedule.appointments_by_day_and_timeslot[day][timeslot]:
                            if app.judge.judge_id == judge_id:
                                used_timeslots.add(timeslot)
                                break  # fandt et appointment i det her timeslot, ingen grund til at lede videre
            
            total_violations += schedule.timeslots_per_work_day - len(used_timeslots)
    
    return (offset + step * total_violations)


def nr18_unused_timegrain_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    
    if not move.is_delete_move and move.new_day is None and move.new_judge is None and move.new_start_timeslot is None:
        return 0 
    
    affected_pairs = get_affected_judge_day_pairs(schedule, move)
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
    unplanned_meetings = schedule.get_all_unplanned_meetings()
    return offset + step * len(unplanned_meetings)

def nr27_overdue_case_not_planned_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    if move.is_insert_move:
        return -(offset + step)  # Negative because we're reducing violations
    elif move.is_delete_move:
        return offset + step
    else:
        return 0  # Regular moves don't change the number of unplanned meetings

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
    
    if not move.is_delete_move and (move.new_day is None and move.new_judge is None and move.new_start_timeslot is None and move.new_room is None):
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

def nr31_distance_between_meetings_full(schedule: Schedule):
    """
    Tjekker hvor langt der er mellem hvert møde
    """
    
    offset = 0
    step = 1
    violations = 0
    
    violations = 0
    
    judges = schedule.get_all_judges()
    for judge in judges:
        violations += calculate_gaps_between_appointments(schedule, judge.judge_id)
        
    return (offset + step * violations)

def nr31_distance_between_meetings_delta(schedule: Schedule, move: Move):
    """
    Tjekker hvor langt der er mellem hvert møde
    """
    if not move.is_delete_move and move.new_day is None and move.new_judge is None and move.new_start_timeslot is None:
        return 0 
    
    offset = 0
    step = 1
    before_violations = 0
    
    affected_pairs = get_affected_judge_day_pairs(schedule, move)
    for day, judge in affected_pairs:
        before_violations += calculate_gaps_between_appointments(schedule, judge, day)  
        
    do_move(move, schedule)
    
    new_last_day = schedule.work_days
    if new_last_day > schedule.work_days:
        for judge in schedule.get_all_judges():
            affected_pairs.add((new_last_day, judge.judge_id))
    
    after_violations = 0
    for day, judge in affected_pairs:
        after_violations += calculate_gaps_between_appointments(schedule, judge, day)
    undo_move(move, schedule)
    
    return (offset + step * (after_violations - before_violations))