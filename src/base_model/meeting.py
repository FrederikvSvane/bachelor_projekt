from dataclasses import dataclass
from typing import Any

from src.base_model.judge import Judge
from src.base_model.room import Room

@dataclass
class Meeting:
    """Class representing a meeting for a court case"""
    meeting_id: int
    meeting_duration: int  # in minutes
    duration_of_stay: int  # How long the case has layed before getting scheduled
    judge: Judge
    room: Room
    case: Any  # Use Any to avoid circular import
    
    def __str__(self):
        return f"{self.meeting_id}"
    
    def __eq__(self, other):
        if not isinstance(other, Meeting):
            return False
        
        # we compare case by like this only to avoid circular dependency
        case_equal = (isinstance(self.case, type(other.case)) and 
                    self.case.case_id == other.case.case_id and
                    self.case.characteristics == other.case.characteristics and
                    self.case.judge_requirements == other.case.judge_requirements and
                    self.case.room_requirements == other.case.room_requirements)
        
        return (self.meeting_id == other.meeting_id and
                self.meeting_duration == other.meeting_duration and
                self.duration_of_stay == other.duration_of_stay and
                self.judge == other.judge and  
                self.room == other.room and    
                case_equal)