from dataclasses import dataclass, field
from typing import Set

from src.base_model.attribute_enum import Attribute

@dataclass
class Room:
    """Class representing a court room"""
    room_id: int
    characteristics: Set[Attribute] = field(default_factory=set)
    case_requirements: Set[Attribute] = field(default_factory=set)
    judge_requirements: Set[Attribute] = field(default_factory=set)
    
    def __str__(self):
        #char_str = ", ".join(str(char) for char in self.characteristics)
        #return f"Room(id={self.room_id}, chars=[{char_str}])"
        return f"{self.room_id}"
    
    def __eq__(self, other):
        if not isinstance(other, Room):
            return False
        
        return (self.room_id == other.room_id and
                self.characteristics == other.characteristics and
                self.case_requirements == other.case_requirements and
                self.judge_requirements == other.judge_requirements)
        