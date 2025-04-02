from dataclasses import dataclass

from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.meeting import Meeting

@dataclass
class Appointment:
    """Class representing a scheduled appointment"""
    meeting: Meeting
    judge: Judge
    room: Room
    day: int # 1-indexed
    timeslot_in_day: int # 1-indexed
        
    def __str__(self):
        return (f"Appointment(M{self.meeting}, "
                f"J{self.judge}, R{self.room}, "
                f"T{self.timeslot_in_day}, "
                f"D{self.day})")
                
def print_appointments(appointments: list[Appointment]):
    for app in appointments:
        print(app)
        