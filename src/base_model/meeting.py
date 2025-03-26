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
    case: Any  # Use Any to avoid the import
    
    def __str__(self):
        return f"{self.meeting_id}"