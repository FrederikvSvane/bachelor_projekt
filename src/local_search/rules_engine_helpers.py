from src.base_model.schedule import Schedule
from src.local_search.move import Move

def get_affected_entities_for_room_stability(schedule: Schedule, move: Move):
    affected_day_judge_pairs = set()
    
    if move.new_day is not None:
        affected_day_judge_pairs.add((move.new_day, move.old_judge.judge_id))
    pass


def get_all_appointments_starting_from_timeslot(schedule: Schedule, day: int, timeslot_start: int, timeslot_end: int):
    appointments = []
    
    # Find all the appointments that are in the range timeslot_start and timeslot_end in the given day
    # For all the appointments_by_day in the timeslot range
    
    
        