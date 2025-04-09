from dataclasses import dataclass, field
from typing import Set, List, Any

from src.base_model.meeting import Meeting
from src.base_model.attribute_enum import Attribute

@dataclass
class Case:
    """Class representing a court case"""
    case_id: int
    characteristics: Set[Attribute] = field(default_factory=set)
    judge_requirements: Set[Attribute] = field(default_factory=set)
    room_requirements: Set[Attribute] = field(default_factory=set)
    meetings: list[Meeting] = field(default_factory=list)  # Use Any to avoid the import
    
    def __str__(self):
        return f"{self.case_id}"
    
    def __eq__(self, other):
        if not isinstance(other, Case):
            return False
        
        self_meeting_ids = {m.meeting_id for m in self.meetings}
        other_meeting_ids = {m.meeting_id for m in other.meetings}
        
        return (self.case_id == other.case_id and
                self.characteristics == other.characteristics and
                self.judge_requirements == other.judge_requirements and
                self.room_requirements == other.room_requirements and
                self_meeting_ids == other_meeting_ids)