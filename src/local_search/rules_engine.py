import math
from collections import defaultdict

from src.base_model.case import Case
from src.base_model.meeting import Meeting
from src.base_model.schedule import Schedule
from src.base_model.appointment import Appointment, print_appointments
from src.base_model.compatibility_checks import check_case_judge_compatibility, check_case_room_compatibility, check_judge_room_compatibility, case_room_matrix
from src.local_search.rules_engine_helpers import *
from src.local_search.move import Move, do_move, undo_move

hard_constraint_weight = None
medium_constraint_weight = None 
soft_constraint_weight = None

def _initialize_constraint_weights(schedule: Schedule) -> None:
    """Initialize constraint weights based on schedule dimensions"""
    global hard_constraint_weight, medium_constraint_weight, soft_constraint_weight
    hard_constraint_weight, medium_constraint_weight, soft_constraint_weight = _calculate_constraint_weights(schedule)

def _calculate_constraint_weights(schedule: Schedule) -> tuple[int, int, int]:
    """
    Calculate appropriate constraint weights based on schedule dimensions.
    Weights are rounded to the nearest power of 10 for readability.
    
    Ensures the constraint hierarchy is maintained:
    - All soft constraint violations combined < one medium constraint violation
    - All medium constraint violations combined < one hard constraint violation
    
    Returns:
        Tuple of (hard_weight, medium_weight, soft_weight)
    """
    n_judges = len(schedule.get_all_judges())
    n_timeslots = schedule.timeslots_per_work_day
    n_days = schedule.work_days
    
    max_possible_violations = n_judges * n_timeslots * n_days
    
    # Set base weight for soft constraints
    soft_weight = 1
    
    # Calculate medium weight - ensure it's larger than all possible soft violations
    # Add safety factor and round to nearest power of 10
    exact_medium_weight = max_possible_violations * soft_weight * 10
    medium_log = round(math.log10(exact_medium_weight))
    medium_weight = 10 ** medium_log
    
    exact_hard_weight = max_possible_violations * medium_weight * 10
    hard_log = round(math.log10(exact_hard_weight))
    hard_weight = 10 ** hard_log
    
    # print(f"Calculated constraint weights based on {n_judges} judges, {n_timeslots} timeslots, {n_days} days:")
    # print(f"  - Soft constraint weight: {soft_weight}")
    # print(f"  - Medium constraint weight: {medium_weight} (10^{medium_log})")
    # print(f"  - Hard constraint weight: {hard_weight} (10^{hard_log})")
    
    return hard_weight, medium_weight, soft_weight


def calculate_full_score(schedule: Schedule) -> list[int]:
    if hard_constraint_weight is None:
        _initialize_constraint_weights(schedule)
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

    full_score = hard_violations * hard_constraint_weight + medm_violations * medium_constraint_weight + soft_violations * soft_constraint_weight
    
    # print(f"FULL: Hard Violations: {hard_violations}, Medium Violations: {medm_violations}, Soft Violations: {soft_violations} (including {unplanned_meetings} unplanned meetings)")  
    
    return [full_score, hard_violations, medm_violations, soft_violations]

def calculate_delta_score(schedule: Schedule, move: Move) -> int:
    """
    do the move AFTER calling this function.
    NOT BEFORE!!!
    """
    if move is None or move.is_applied:
        raise ValueError("Move is None or already applied.")
    
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
    soft_violations += nr19_case_has_specific_judge_delta(schedule, move)
    soft_violations += nr20_max_weekly_coverage_delta(schedule, move)
    soft_violations += nr21_all_meetings_planned_for_case_delta(schedule, move)
    soft_violations += nr29_room_stability_per_day_delta(schedule, move)
    soft_violations += nr31_distance_between_meetings_delta(schedule, move)

    delta_score = hard_constraint_weight * hard_violations + medium_constraint_weight * medm_violations + soft_constraint_weight * soft_violations

    #print(f"DELTA: Hard Violations: {hard_violations}, Medium Violations: {medm_violations}, Soft Violations: {soft_violations}")  
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
    
    if move.is_insert_move:
        # only possible violation is if the room and meeting are incompatible after inserting
        # the meeting was unplanned before, so we don't care about the old room
        return 0 if check_case_room_compatibility(case_id, move.new_room.room_id) else len(move.appointments)
    
    if not move.is_delete_move and not move.is_insert_move and move.new_room is None:
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
    
    if move.is_insert_move:
        # only possible violation is if the judge and meeting are incompatible after inserting
        # the meeting was unplanned before, so we don't care about the old judge
        return 0 if check_case_judge_compatibility(case_id, move.new_judge.judge_id) else len(move.appointments)
    
    if not move.is_delete_move and not move.is_insert_move and move.new_judge is None:
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
    
    if move.is_insert_move:
        # only possible violation is if the judge and meeting are incompatible after inserting
        # the meeting was unplanned before, so we don't care about the old judge
        return 0 if check_case_judge_compatibility(case_id, move.new_judge.judge_id) else len(move.appointments)
    
    if not move.is_delete_move and not move.is_insert_move and move.new_judge is None:
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

    is_relevant_change = (move.is_delete_move or move.is_insert_move or
                          move.new_judge is not None or
                          move.new_day is not None or
                          move.new_start_timeslot is not None)
    if not is_relevant_change:
         only_changing_room = (move.new_room is not None and move.new_judge is None and
                              move.new_day is None and move.new_start_timeslot is None)
         if only_changing_room: return 0
         elif move.new_room is None and move.new_judge is None and move.new_day is None and move.new_start_timeslot is None: return 0

    original_work_days = schedule.work_days
    affected_pairs = get_affected_judge_day_pairs(schedule, move)

    if not affected_pairs:
         return 0

    before_violations = calculate_unused_timeslots_for_all_judge_day_pairs(
        schedule, affected_pairs, original_work_days
    )

    do_move(move, schedule)
    current_work_days = schedule.work_days

    after_violations = calculate_unused_timeslots_for_all_judge_day_pairs(
        schedule, affected_pairs, current_work_days
    )

    undo_move(move, schedule)

    if schedule.work_days != original_work_days:
        schedule.work_days = original_work_days

    return (offset + step * (after_violations - before_violations))

def nr19_case_has_specific_judge_full(schedule: Schedule):
    offset = 0
    step = 1
    violations = 0
    cases: list[Case] = schedule.get_all_cases()

    for case in cases:
        unplanned_meetings = 0
        case_meetings: list[Meeting] = case.meetings
        if not case_meetings or (len(case_meetings) == 1 and case_meetings[0].judge is not None):  # Skip cases with only one meeting, which is planned
            continue
        
        # Collect all unique judges for this case
        judges_set = set()
        for meeting in case_meetings:
            if not meeting.judge or meeting.judge is None:
                unplanned_meetings += 1
            else:
                judges_set.add(meeting.judge)
        
        # If more than one judge, add violations
        if len(judges_set) + unplanned_meetings > 1:
            violations += len(judges_set) - 1 + unplanned_meetings  # Count each extra judge as a violation

    return (offset + step * violations) 

def nr19_case_has_specific_judge_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1



    if move.new_judge is None and not move.is_delete_move:
        return 0

    affected_case: Case = move.appointments[0].meeting.case
    case_meetings: list[Meeting] = affected_case.meetings

    if not case_meetings or (len(case_meetings) == 1 and case_meetings[0].judge is not None): # case has only one meeting, and that meeting is planned.
        return 0
    
    # Before move: collect unique judges
    unplanned_meetings = 0
    before_judges = set()
    for meeting in case_meetings:
        if not meeting.judge or meeting.judge is None:
            unplanned_meetings += 1
        else:
            before_judges.add(meeting.judge)
    before_violations = len(before_judges) + unplanned_meetings - 1 if (len(before_judges) + unplanned_meetings) > 1 else 0

    # Apply move
    do_move(move, schedule)
    
    # After move: collect unique judges
    unplanned_meetings = 0
    after_judges = set()
    for meeting in case_meetings:
        if not meeting.judge or meeting.judge is None:
          unplanned_meetings += 1
        else:
          after_judges.add(meeting.judge)
    after_violations = len(after_judges) + unplanned_meetings - 1 if (len(after_judges) + unplanned_meetings) > 1 else 0
    
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
    
    is_normal_move = not move.is_delete_move and not move.is_insert_move
    only_changing_room = move.new_day is None and move.new_judge is None and move.new_start_timeslot is None
    
    if is_normal_move and only_changing_room:
        return 0  # No change in day or judge, x no impact on weekly coverage
    
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

def nr27_overdue_case_not_planned_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    

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
        #check_app_and_meeting_same_judge_and_room(schedule, appointment.meeting)
        day_judge_pairs.add((appointment.day, appointment.judge.judge_id))
    
    for day, judge_id in day_judge_pairs:
        violations += count_room_changes_for_day_judge_pair(schedule, day, judge_id)
    
    return (offset + step * violations)
                

def nr29_room_stability_per_day_delta(schedule: Schedule, move: Move):
    offset = 0
    step = 1
    
    if not move.is_delete_move and (move.new_day is None and move.new_judge is None and move.new_start_timeslot is None and move.new_room is None):
        return 0 # probably wont ever happen, but fine to have for future delete moves i guess

    affected_day_judge_pairs = get_affected_judge_day_pairs(schedule, move)
    
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
    
    violations += schedule.work_days - 1  # Add one violation for each day without meetings
        
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
    
    before_violations += schedule.work_days - 1  # Add one violation for each day without meetings
        
    do_move(move, schedule)
    
    new_last_day = schedule.work_days
    if new_last_day > schedule.work_days:
        for judge in schedule.get_all_judges():
            affected_pairs.add((new_last_day, judge.judge_id))
    
    after_violations = 0
    for day, judge in affected_pairs:
        after_violations += calculate_gaps_between_appointments(schedule, judge, day)

    after_violations += schedule.work_days - 1  # Add one violation for each day without meetings
    
    undo_move(move, schedule)
    
    return (offset + step * (after_violations - before_violations))