from dataclasses import dataclass, field
from typing import Set

from attribute_enum import Attribute

@dataclass
class Case:
    """Class representing a court case"""
    case_id: int
    case_duration: int  # in minutes
    characteristics: Set[Attribute] = field(default_factory=set)
    judge_requirements: Set[Attribute] = field(default_factory=set)
    room_requirements: Set[Attribute] = field(default_factory=set)
    
    def __str__(self):
        char_str = ", ".join(str(char) for char in self.characteristics)
        req_str = ", ".join(str(req) for req in self.judge_requirements)
        return f"Case(id={self.case_id}, duration={self.case_duration}, chars=[{char_str}], reqs=[{req_str}])"
