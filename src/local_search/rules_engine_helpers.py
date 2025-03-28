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
    appointments_in_day = schedule.get_appointments_in_timeslot_range(day=day, start_slot=1, end_slot=schedule.timeslots_per_work_day)

    
    appointments_for_judge = [a for a in appointments_in_day if a.judge.judge_id == judge_id]


    appointments_for_judge.sort(key=lambda a: (a.timeslot_in_day, a.meeting.meeting_id))

    current_room_id = None
    violations = 0
    for appointment in appointments_for_judge:
        if current_room_id is not None and appointment.room.room_id != current_room_id:
            violations += 1
        current_room_id = appointment.room.room_id
    
    return violations



    
