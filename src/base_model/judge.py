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
        char_str = ", ".join(str(char) for char in self.characteristics)
        return f"Judge(id={self.judge_id}, chars=[{char_str}])"