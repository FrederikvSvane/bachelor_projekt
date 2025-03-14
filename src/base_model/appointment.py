from dataclasses import dataclass

from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.room import Room

@dataclass
class Appointment:
    """Class representing a scheduled appointment"""
    case: Case
    judge: Judge
    room: Room
    day: int
    timeslot_start: int
    timeslots_duration: int
    
    def __str__(self):
        return (f"Appointment(case_id={self.case.case_id}, "
                f"judge_id={self.judge.judge_id}, room_id={self.room.room_id}, "
                f"day={self.day}, start={self.timeslot_start}, "
                f"duration={self.timeslots_duration})")