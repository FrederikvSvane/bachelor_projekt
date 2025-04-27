from collections import defaultdict
from sys import exit
import math

from src.base_model.schedule import Schedule
from src.base_model.appointment import Appointment
from src.base_model.meeting import Meeting
from src.base_model.case import Case
from src.base_model.compatibility_checks import check_case_judge_compatibility, check_case_room_compatibility, check_judge_room_compatibility
from src.local_search.move import Move, do_move, undo_move
from src.local_search.rules_engine_helpers import *


# 2 ooms scale difference per category
hard_containt_weight = 10_000
medm_containt_weight = 100
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
    soft_violations += nr19_case_has_specific_judge_full(schedule)
    soft_violations += nr20_max_weekly_coverage_full(schedule)
    soft_violations += nr21_all_meetings_planned_for_case_full(schedule)
    soft_violations += nr29_room_stability_per_day_full(schedule)
    soft_violations += nr31_distance_between_meetings_full(schedule)

    full_score = hard_violations * hard_containt_weight + medm_violations * medm_containt_weight + soft_violations * soft_containt_weight
    
    print(f"Hard Violations: {hard_violations}, Medium Violations: {medm_violations}, Soft Violations: {soft_violations}")  
    
    return full_score

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
    hard_violations += nr1_overbooked_room_in_timeslot_delta(schedule, move)
    hard_violations += nr2_overbooked_judge_in_timeslot_delta(schedule, move)
    hard_violations += nr6_virtual_room_must_have_virtual_meeting_delta(schedule, move)
    hard_violations += nr8_judge_skillmatch_delta(schedule, move)
    hard_violations += nr14_virtual_case_has_virtual_judge_delta(schedule, move)

    # Medium rules
    medm_violations = 0
    medm_violations += nr18_unused_timegrain_delta(schedule, move)
    # medm_violations += nr17_unused_timeblock_delta(schedule, move)

    # Soft rules
    soft_violations = 0    
    soft_violations += nr19_case_has_specific_judge_delta(schedule, move)
    soft_violations += nr20_max_weekly_coverage_delta(schedule, move)
    soft_violations += nr21_all_meetings_planned_for_case_delta(schedule, move)
    soft_violations += nr29_room_stability_per_day_delta(schedule, move)
    soft_violations += nr31_distance_between_meetings_delta(schedule, move)

    delta_score = hard_containt_weight * hard_violations + medm_containt_weight * medm_violations + soft_containt_weight * soft_violations

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
        if day in schedule.appointments_by_day_and_timeslot:
            for timeslot in range(1, schedule.timeslots_per_work_day + 1):
                if timeslot in schedule.appointments_by_day_and_timeslot[day]:
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

def nr6_virtual_room_must_have_virtual_meeting_delta(_: Schedule, move: Move):
    if move.new_room is None:
        return 0
    
    offset = 0
    step = 1
    
    case_id: int = move.appointments[0].meeting.case.case_id
    
    old_room_has_compatibility = check_case_room_compatibility(case_id, move.old_room.room_id)
    new_room_has_compatibility = check_case_room_compatibility(case_id, move.new_room.room_id)
    
    if old_room_has_compatibility and not new_room_has_compatibility: # was compatible, now incompatible => Adding violations
        violations = len(move.appointments)
    elif not old_room_has_compatibility and new_room_has_compatibility: # was incompatible, now compatible => Removing violations
        violations = -len(move.appointments)
    else:
        violations = 0

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

def nr8_judge_skillmatch_delta(_: Schedule, move: Move):
    if move.new_judge is None:
        return 0
    
    offset = 0
    step = 1
    
    case_id: int = move.appointments[0].meeting.case.case_id
    
    old_judge_has_skills = check_case_judge_compatibility(case_id, move.old_judge.judge_id)
    new_judge_has_skills = check_case_judge_compatibility(case_id, move.new_judge.judge_id)
    
    if old_judge_has_skills and not new_judge_has_skills: # was compatible, now incompatible => Adding violations
        violations = len(move.appointments)
    elif not old_judge_has_skills and new_judge_has_skills: # was incompatible, now compatible => Removing violations
        violations = -len(move.appointments)
    else:
        violations = 0

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

def nr14_virtual_case_has_virtual_judge_delta(_: Schedule, move: Move):
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

    if old_judge_is_virtual and not new_room_case_compatible: # was compatible, now incompatible => Adding violations
        violations = len(move.appointments)
    elif not old_judge_is_virtual and new_room_case_compatible: # was incompatible, now compatible => Removing violations
        violations = -len(move.appointments)
    else:
        violations = 0

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
    
    if move.new_day is None and move.new_judge is None and move.new_start_timeslot is None:
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
    violations = 0
    cases: list[Case] = schedule.get_all_cases()

    for case in cases:
        case_meetings: list[Meeting] = case.meetings
        if not case_meetings or len(case_meetings) == 1:  # Skip cases with no/single meetings
            continue
        
        # Collect all unique judges for this case
        judges_set = set()
        for meeting in case_meetings:
            judges_set.add(meeting.judge)
        
        # If more than one judge, add violations
        if len(judges_set) > 1:
            violations += len(judges_set) - 1  # Count each extra judge as a violation

    return (offset + step * violations) 

def nr19_case_has_specific_judge_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1

    if move.new_judge is None:
        return 0

    affected_case: Case = move.appointments[0].meeting.case
    case_meetings: list[Meeting] = affected_case.meetings

    if not case_meetings or len(case_meetings) == 1:
        return 0
    
    # Before move: collect unique judges
    before_judges = set()
    for meeting in case_meetings:
        before_judges.add(meeting.judge)
    before_violations = len(before_judges) - 1 if len(before_judges) > 1 else 0

    # Apply move
    do_move(move, schedule)
    
    # After move: collect unique judges
    after_judges = set()
    for meeting in case_meetings:
        after_judges.add(meeting.judge)
    after_violations = len(after_judges) - 1 if len(after_judges) > 1 else 0
    
    # Restore original state
    undo_move(move, schedule)

    return (offset + step * (after_violations - before_violations))

def nr20_max_weekly_coverage_full(schedule: Schedule, max_percentage: float = 0.8):
    """
    Calculate violations for maximum weekly coverage rule.
    A judge should not be scheduled for more than max_percentage of available timeslots in a week.
    Violations are counted as the percentage points exceeding the maximum.
    """
    offset = 0
    step = 1
    violations = 0
    
    # Get all judge-week pairs
    week_judge_pairs = get_week_judge_pairs(schedule)
    
    for judge_id, week_number in week_judge_pairs:
        occupied, total = count_weekly_coverage_for_judge_week(schedule, judge_id, week_number)
        
        if total > 0:
            coverage_percentage = occupied / total
            if coverage_percentage > max_percentage:
                # Calculate percentage points over the limit
                excess_percentage = coverage_percentage - max_percentage
                # Convert to percentage points (0-100 scale) and round up
                excess_points = math.ceil(excess_percentage * 100)
                violations += excess_points
    
    return offset + step * violations

def nr20_max_weekly_coverage_delta(schedule: Schedule, move: Move, max_percentage: float = 0.8):
    """
    Calculate delta for maximum weekly coverage rule when making a move.
    Violations are counted as the percentage points exceeding the maximum.
    """
    offset = 0
    step = 1
    
    if move.new_day is None and move.new_judge is None and move.new_start_timeslot is None:
        return 0  # No change in day or judge, so no impact on weekly coverage
    
    # Get affected judge-week pairs
    affected_week_judge_pairs = get_affected_week_judge_pairs(schedule, move)
    
    # Calculate violations before move
    before_violations = 0
    for judge_id, week_number in affected_week_judge_pairs:
        occupied, total = count_weekly_coverage_for_judge_week(schedule, judge_id, week_number)
        if total > 0:
            coverage_percentage = occupied / total
            if coverage_percentage > max_percentage:
                excess_percentage = coverage_percentage - max_percentage
                excess_points = math.ceil(excess_percentage * 100)
                before_violations += excess_points
    
    # Apply move
    do_move(move, schedule)
    
    # Calculate violations after move
    after_violations = 0
    for judge_id, week_number in affected_week_judge_pairs:
        occupied, total = count_weekly_coverage_for_judge_week(schedule, judge_id, week_number)
        if total > 0:
            coverage_percentage = occupied / total
            if coverage_percentage > max_percentage:
                excess_percentage = coverage_percentage - max_percentage
                excess_points = math.ceil(excess_percentage * 100)
                after_violations += excess_points
    
    # Undo move
    undo_move(move, schedule)
    
    return offset + step * (after_violations - before_violations)

def nr21_all_meetings_planned_for_case_full(schedule: Schedule):
    offset = 0
    step = 1
    unplanned_meetings = schedule.get_all_unplanned_meetings()
    return offset + step * len(unplanned_meetings)

def nr21_all_meetings_planned_for_case_delta(schedule: Schedule, move: Move):

    if move.new_day is None and move.new_judge is None and move.new_start_timeslot is None:
        return 0
    offset = 0
    step = 1
    if move.is_insert_move:
        return -(offset + step)  # Negative because we're reducing violations
    elif move.is_delete_move:
        return offset + step
    else:
        return 0 

def nr22_case_meetings_too_sparsely_planned_full(schedule: Schedule):
    offset = 0
    step = 1
    pass

def nr22_case_meetings_too_sparsely_planned_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    pass


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
    if move.new_day is None and move.new_judge is None and move.new_start_timeslot is None:
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