from dataclasses import dataclass
from enum import Enum
from math import ceil
from typing import List, Dict


class Sagstype(Enum):
    """Enum representing different types of court cases."""
    STRAFFE = 0 
    CIVIL = 1   
    TVANG = 2
    
    @classmethod
    def get_number_of_sagstyper(cls): # cls is short for class. like self. just works
        """Return the number of case types available."""
        return len(cls)
    
    def __str__(self):
        return self.name.capitalize()
    
    @classmethod
    def from_string(cls, string_value):
        """Convert a string to the appropriate Sagstype enum value."""
        normalized = string_value.upper()
        if normalized == "STRAFFE":
            return cls.STRAFFE
        elif normalized == "CIVIL":
            return cls.CIVIL
        elif normalized == "TVANG":
            return cls.TVANG
        else:
            raise ValueError(f"Invalid Sagstype string: {string_value}")


@dataclass
class Meeting:
    """Class representing a court meeting/case."""
    meeting_id: int
    meeting_duration: int  # in minutes
    meeting_sagstype: Sagstype
    meeting_virtual: bool
    
    def __str__(self):
        return (f"Meeting(id={self.meeting_id}, duration={self.meeting_duration}, "
                f"type={self.meeting_sagstype}, virtual={self.meeting_virtual})")


@dataclass
class Judge:
    """Class representing a judge."""
    judge_id: int
    judge_skills: List[Sagstype]
    judge_virtual: bool
    
    def has_skill(self, skill: Sagstype) -> bool:
        """Check if judge has a specific skill."""
        return skill in self.judge_skills
    
    def __str__(self):
        skills_str = ", ".join(str(skill) for skill in self.judge_skills)
        return f"Judge(id={self.judge_id}, skills=[{skills_str}], virtual={self.judge_virtual})"


@dataclass
class Room:
    """Class representing a court room."""
    room_id: int
    room_virtual: bool
    
    def __str__(self):
        return f"Room(id={self.room_id}, virtual={self.room_virtual})"


@dataclass
class Appointment:
    """Class representing a scheduled appointment."""
    meeting: Meeting
    judge: Judge
    room: Room
    day: int
    timeslot_start: int
    timeslots_duration: int
    
    def __str__(self):
        return (f"Appointment(meeting_id={self.meeting.meeting_id}, "
                f"judge_id={self.judge.judge_id}, room_id={self.room.room_id}, "
                f"day={self.day}, start={self.timeslot_start}, "
                f"duration={self.timeslots_duration})")


def judge_has_skill(judge: Judge, skill: Sagstype) -> bool:
    """Check if a judge has a specific skill."""
    return skill in judge.judge_skills


def calculate_all_judge_capacities(meetings: List[Meeting], judges: List[Judge]) -> Dict[int, int]:
    """
    Calculate the capacities of all judges such that the sum of their capacities equals the total number of meetings.

    Args:
        meetings: List of Meeting objects, each with a case type (meeting_sagstype).
        judges: List of Judge objects, each with an ID (judge_id) and skills (judge_skills).

    Returns:
        Dict[int, int]: A dictionary mapping each judge's ID to their calculated capacity.
    """
    # Step 1: Get unique case types and count total unique types (m)
    case_types = set(meeting.meeting_sagstype for meeting in meetings)
    m = len(case_types)

    # Step 2: Count the number of meetings per case type
    case_counts = {}
    for meeting in meetings:
        case_type = meeting.meeting_sagstype
        case_counts[case_type] = case_counts.get(case_type, 0) + 1

    # Step 3: Calculate weights for each judge per case type
    judge_weights = {}
    for judge in judges:
        k = len(judge.judge_skills)  # Number of skills for this judge
        judge_weights[judge.judge_id] = {}
        for case_type in case_types:
            # Weight is m - k + 1 if the judge can handle the case type, else 0
            judge_weights[judge.judge_id][case_type] = max(1, m-k+1) if case_type in judge.judge_skills else 0

    # Step 4: Calculate total weights per case type across all judges
    total_weights = {}
    for case_type in case_types:
        total_weights[case_type] = sum(judge_weights[judge.judge_id][case_type] for judge in judges)

    # Step 5: Calculate floating-point capacities for each judge
    float_capacities = {}
    for judge in judges:
        capacity = 0.0
        for case_type in case_types:
            if case_type in judge.judge_skills and total_weights[case_type] > 0:
                # Proportion of meetings for this case type assigned to this judge
                proportion = judge_weights[judge.judge_id][case_type] / total_weights[case_type]
                capacity += proportion * case_counts[case_type]
        float_capacities[judge.judge_id] = capacity

    # Step 6: Floor the capacities to get initial integer values
    int_capacities = {judge_id: int(cap) for judge_id, cap in float_capacities.items()}

    # Step 7: Calculate remaining meetings to distribute
    total_meetings = len(meetings)
    current_sum = sum(int_capacities.values())
    remaining = total_meetings - current_sum

    # Step 8: Distribute remaining meetings based on largest remainders
    if remaining > 0:
        # Calculate fractional remainders for each judge
        remainders = [
            (judge.judge_id, float_capacities[judge.judge_id] - int_capacities[judge.judge_id])
            for judge in judges if float_capacities[judge.judge_id] > 0
        ]
        # Sort by remainder in descending order
        # Add one meeting to the top 'remaining' judges
        for _ in range(remaining):
            remainders.sort(key=lambda x: x[1], reverse=True)
            judge_id, remainder = remainders[0]
            int_capacities[judge_id] += 1
            remainders[0] = (judge_id, remainder - 1.0)

    return int_capacities



# optional wrapper. expensive to use. try to return all by using the function above and then just index them
def calculate_judge_capacity(meetings: List[Meeting], judges: List[Judge], judge_id: int) -> int:
    """
    Calculate the capacity for a single judge by computing all capacities and extracting the desired one.

    Args:
        meetings: List of Meeting objects.
        judges: List of Judge objects.
        judge_id: The ID of the judge whose capacity is requested.

    Returns:
        int: The capacity of the specified judge.
    """
    all_capacities = calculate_all_judge_capacities(meetings, judges)
    return all_capacities.get(judge_id, 0)