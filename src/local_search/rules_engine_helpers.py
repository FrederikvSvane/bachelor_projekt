from src.base_model.schedule import Schedule
from src.local_search.move import Move

def get_affected_pairs_for_room_stability(schedule: Schedule, move: Move):
    affected_day_judge_pairs = set()
    
    affected_day_judge_pairs.add((move.old_day, move.old_judge.judge_id)) # original day and judge

    if move.new_day is not None:
        affected_day_judge_pairs.add((move.new_day, move.old_judge.judge_id))
    
    if move.new_judge is not None:
        affected_day_judge_pairs.add((move.old_day, move.new_judge.judge_id))
    
    if move.new_day is not None and move.new_judge is not None:
        affected_day_judge_pairs.add((move.new_day, move.new_judge.judge_id))
    
    return affected_day_judge_pairs

def count_room_changes_for_day_judge_pair(schedule: Schedule, day: int, judge_id: int):
    appointments = [app for app in schedule.appointments if app.day == day and app.judge.judge_id == judge_id]  # TODO This might defeat the purpose. Should we maintain a dict of appointments by day, to avoid having to loop through all?
    appointments.sort(key=lambda a: a.timeslot_in_day)
    
    current_room_id = None
    violations = 0
    for appointment in appointments:
        if current_room_id is not None and appointment.room.room_id != current_room_id:
            violations += 1
        current_room_id = appointment.room.room_id
    
    return violations

def get_all_appointments_starting_from_timeslot(schedule: Schedule, day: int, timeslot_start: int, timeslot_end: int):
    appointments = []
    
    # Find all the appointments that are in the range timeslot_start and timeslot_end in the given day
    # For all the appointments_by_day in the timeslot range
    
