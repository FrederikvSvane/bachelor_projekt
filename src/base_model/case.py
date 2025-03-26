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
    meetings: List[Meeting] = field(default_factory=list)  # Use Any to avoid the import
    
    def __str__(self):
        return f"{self.case_id}"