from dataclasses import dataclass, field
from typing import Set

from src.base_model.attribute_enum import Attribute

@dataclass
class Judge:
    """Class representing a judge"""
    judge_id: int
    characteristics: Set[Attribute] = field(default_factory=set)
    case_requirements: Set[Attribute] = field(default_factory=set)
    room_requirements: Set[Attribute] = field(default_factory=set)
    
    def __str__(self):
        return f"{self.judge_id}"
    
    def __eq__(self, other):
        if not isinstance(other, Judge):
            return False
        
        return (self.judge_id == other.judge_id and
                self.characteristics == other.characteristics and
                self.case_requirements == other.case_requirements and
                self.room_requirements == other.room_requirements)
    
    def __hash__(self):
        return hash(self.judge_id)