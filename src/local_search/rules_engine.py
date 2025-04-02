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
    appointments.sort(key=lambda a: (a.day, a.timeslot_in_day, a.room.room_id))
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
    move.appointments.sort(key=lambda a: (a.day, a.timeslot_in_day, a.room.room_id))
    
    for app in move.appointments:
        appointments_at_time = schedule.appointments_by_day[app.day][app.timeslot_in_day]
        appointments_at_time.sort(key=lambda a: (a.room.room_id, a.judge.judge_id))
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
    appointments.sort(key=lambda a: (a.day, a.timeslot_in_day, a.judge.judge_id))
    
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
    move.appointments.sort(key=lambda a: (a.day, a.timeslot_in_day, a.judge.judge_id))
    
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
    

def nr6_virtual_room_must_have_virtual_meeting_full(schedule: Schedule):
    offset = 0
    step = 1
    violations = 0
    appointments = schedule.get_all_appointments()
    appointments.sort(key=lambda a: (a.day, a.timeslot_in_day, a.room.room_id))
    
    for app in appointments:
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
    appointments = schedule.get_all_appointments()
    appointments.sort(key=lambda a: (a.day, a.timeslot_in_day, a.judge.judge_id))
    
    for appointment in appointments:
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
    
    appointments = schedule.get_all_appointments()
    appointments.sort(key=lambda a: (a.day, a.timeslot_in_day, a.judge.judge_id))
    
    for app in appointments:
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
    
    if (move.new_day is None and move.new_judge is None and move.new_start_timeslot is None):
        return 0
    
    block_size: int = len(move.appointments)
    new_day = move.new_day if move.new_day is not None else move.old_day
    new_start_timeslot = move.new_start_timeslot if move.new_start_timeslot is not None else move.old_start_timeslot
    new_judge_id = move.new_judge.judge_id if move.new_judge is not None else move.old_judge.judge_id
    
    appointments_in_old_block: list[Appointment] = get_appointments_in_timeslot_range(schedule, start_day=move.old_day, start_slot=move.old_start_timeslot, end_slot=move.old_start_timeslot + len(move.appointments) - 1, judge_id=move.old_judge.judge_id)
    appointments_in_new_block: list[Appointment] = get_appointments_in_timeslot_range(schedule, start_day=new_day, start_slot=new_start_timeslot, end_slot=new_start_timeslot + len(move.appointments) - 1, judge_id=new_judge_id, meeting_id=move.meeting_id)
    
    unused_timeslots_in_new_block: int = get_n_unused_timeslots_in_range(schedule, new_day, new_day, new_start_timeslot, new_start_timeslot + len(move.appointments) - 1, judge_id=new_judge_id, meeting_id=move.meeting_id)
    
    # block_delta = len(appointments_in_old_block) - len(appointments_in_new_block)
    timeslot_delta = 0
    total_possible_timeslots_delta = 0
    
    old_latest_global_timeslot = get_latest_global_timeslot(schedule)
    all_judge_ids = schedule.get_all_judges()

    old_frame = len(all_judge_ids) * old_latest_global_timeslot
    do_move(move, schedule)

    # de her ting kan ske:
    # 1. antallet af appointments i old block er lig med antallet af appointments i move. ie. der er ingen dobble bookings i old block
    if (len(appointments_in_old_block) == len(move.appointments)):
        # 1.1: antallet af appointments i new block er nul. Så vi fjerner ingen dooble bookings, og laver ingen nye dobble bookings (very good also)
        if (len(appointments_in_new_block) == 0):
            pass
        # 1.2: antallet af appointments i new block er større end 0. Så vi fjerner ingen dooble bookings, men tilføjer nye dobble bookings
        if (len(appointments_in_new_block) > 0):
            timeslot_delta = len(move.appointments) - unused_timeslots_in_new_block # we use all the previously unused timeslots in the new block

    # 2. antallet af appointments i old block er større end antallet af appointments i move => der er dobble bookings i old block
    if (len(appointments_in_old_block) > len(move.appointments)):
        unused_timeslots_in_old_block_after_move = get_n_unused_timeslots_in_range(schedule, move.old_day, move.old_day, move.old_start_timeslot, move.old_start_timeslot + len(move.appointments) - 1, judge_id=move.old_judge.judge_id)
        # 2.1: antallet af appointments i new block er nul. Så vi fjerner dobble bookings og tilføjer ingen nye dobble bookings (very good)
        if(len(appointments_in_new_block) == 0):
            timeslot_delta -= unused_timeslots_in_old_block_after_move # FIXME maybe dont work?!
        # 2.2: antallet af appointments i new block er større end nul. Så vi fjerner dobble bookings men tilføjer nye dobble bookings
        if(len(appointments_in_new_block) > 0):
            timeslot_delta = unused_timeslots_in_old_block_after_move - unused_timeslots_in_new_block
    
    new_latest_global_timeslot = get_latest_global_timeslot(schedule)
    new_frame = len(all_judge_ids) * new_latest_global_timeslot
    
    if old_frame != new_frame: # the move doesnt affect the latest global timeslot
        total_possible_timeslots_delta = new_frame - old_frame
    
    violations = total_possible_timeslots_delta + timeslot_delta
     
    undo_move(move, schedule)
    
    return (offset + step * violations)

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
        appointments.sort(key=lambda a: (a.timeslot_in_day, a.meeting.meeting_id, a.room.room_id))
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