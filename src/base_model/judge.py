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