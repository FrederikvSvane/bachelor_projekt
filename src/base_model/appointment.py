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
    
    def __eq__(self, other):
        if not isinstance(other, Appointment):
            return False
        
        return (self.meeting.meeting_id == other.meeting.meeting_id and
                self.judge.judge_id == other.judge.judge_id and
                self.room.room_id == other.room.room_id and
                self.day == other.day and
                self.timeslot_in_day == other.timeslot_in_day)
        
    def __hash__(self):
        return hash((self.meeting.meeting_id, self.judge.judge_id, self.room.room_id, self.day, self.timeslot_in_day))
                
def print_appointments(appointments: list[Appointment]):
    for app in appointments:
        print(app)
        