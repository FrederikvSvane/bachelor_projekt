import random
import math
import json
from typing import Dict, Any, List

from src.models import Meeting, Judge, Room, Sagstype

class TruncatedNormalDistribution:
    """Generates a truncated normal distribution for meeting durations."""
    def __init__(self, mean: float, stddev: float, min_val: float, max_val: float):
        self.mu = mean
        self.sigma = stddev
        self.a = min_val
        self.b = max_val
        
    def erfinv(self, x: float) -> float:
        """Inverse error function implementation."""
        sgn = -1.0 if x < 0 else 1.0
        
        x = (1 - x) * (1 + x)  # x = 1 - x*x
        lnx = math.log(x)
        
        tt1 = 2 / (math.pi * 0.147) + 0.5 * lnx
        tt2 = 1 / 0.147 * lnx
        
        return sgn * math.sqrt(-tt1 + math.sqrt(tt1 * tt1 - tt2))
    
    def standard_normal_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2.0)))
    
    def sample(self, gen: random.Random) -> float:
        """Sample from the truncated normal distribution."""
        alpha = self.standard_normal_cdf((self.a - self.mu) / self.sigma)
        beta = self.standard_normal_cdf((self.b - self.mu) / self.sigma)
        
        # Uniform random number between alpha and beta
        u = gen.random() * (beta - alpha) + alpha
        
        # Return the inverse CDF
        return self.mu + self.sigma * math.sqrt(2.0) * self.erfinv(2.0 * u - 1.0)
    
    def __call__(self, gen: random.Random) -> float:
        """Allow the distribution to be called directly."""
        return self.sample(gen)


def generate_test_data(n_meetings: int, n_judges: int, n_rooms: int, 
                       work_days: int = 5, granularity: int = 15, 
                       min_per_work_day: int = 480, fixed_duration: bool = False) -> Dict[str, Any]:
    """Generate test data for court scheduling."""
    # Initialize random generator
    gen = random.Random()
    
    # Create duration distribution
    duration_dist = TruncatedNormalDistribution(30.0, 80.0, 5.0, 360.0)
    
    # Generate meetings
    meetings = []
    for i in range(1, n_meetings + 1):
        if fixed_duration:
            duration = granularity
        else:
            # Generate duration and round to nearest 5
            raw_duration = duration_dist(gen)
            duration = round(raw_duration / 5.0) * 5
        
        # Generate random case type
        case_type = random.choice(list(Sagstype))
        
        # Generate meeting
        meeting = {
            "id": i,
            "duration": duration,
            "type": str(case_type),
            "virtual": bool(gen.randint(0, 3) == 0)  # 25% chance of being virtual
        }
        meetings.append(meeting)
    
    # Generate judges
    judges = []
    # Track which case types have been covered
    covered_types = set()

    for i in range(1, n_judges + 1):
        all_types = list(Sagstype)
        
        if i == n_judges and len(covered_types) < len(all_types):
            # Last judge - ensure any remaining uncovered types are included
            uncovered = [t for t in all_types if str(t) not in covered_types]
            # Make sure the judge has at least one skill, up to 3 total
            num_additional = min(3 - len(uncovered), len(all_types) - len(uncovered))
            num_additional = max(0, num_additional)  # Ensure non-negative
            
            if num_additional > 0:
                # Add some already covered types if there's room
                covered_list = [t for t in all_types if str(t) in covered_types]
                gen.shuffle(covered_list)
                additional_skills = covered_list[:num_additional]
            else:
                additional_skills = []
                
            skills = uncovered + additional_skills
        else:
            # For judges before the last one, assign random skills
            gen.shuffle(all_types)
            num_skills = min(3, max(1, gen.randint(1, 3)))  # Between 1 and 3 skills
            skills = all_types[:num_skills]
        
        # Update the covered types
        for skill in skills:
            covered_types.add(str(skill))
        
        # Generate judge
        judge = {
            "id": i,
            "skills": [str(skill) for skill in skills],
            "virtual": bool(gen.randint(0, 3) == 0)  # 25% chance of being virtual
        }
        judges.append(judge)
    
    # Generate rooms
    rooms = []
    for i in range(1, n_rooms + 1):
        room = {
            "id": i,
            "virtual": bool(gen.randint(0, 3) == 0)  # 25% chance of being virtual
        }
        rooms.append(room)
    
    # Create final data structure
    data = {
        "work_days": work_days,
        "min_per_work_day": min_per_work_day,
        "granularity": granularity,
        "meetings": meetings,
        "judges": judges,
        "rooms": rooms
    }
    
    # Save test data to a file for reference (optional)
    with open('sample_input.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    return data


def generate_test_data_parsed(n_meetings: int, n_judges: int, n_rooms: int, 
                             work_days: int = 5, granularity: int = 15, 
                             min_per_work_day: int = 480) -> Dict:
    """Generate and parse test data into model objects."""
    # Generate raw test data
    test_data = generate_test_data(n_meetings, n_judges, n_rooms, 
                                  work_days, granularity, min_per_work_day)
    
    # Parse the data into model objects
    parsed_data = {
        "work_days": test_data["work_days"],
        "min_per_work_day": test_data["min_per_work_day"],
        "granularity": test_data["granularity"],
        "meetings": [],
        "judges": [],
        "rooms": []
    }
    
    # Parse meetings
    for meeting_data in test_data["meetings"]:
        meeting = Meeting(
            meeting_id=meeting_data["id"],
            meeting_duration=meeting_data["duration"],
            meeting_sagstype=Sagstype.from_string(meeting_data["type"]),
            meeting_virtual=meeting_data["virtual"]
        )
        parsed_data["meetings"].append(meeting)
    
    # Parse judges
    for judge_data in test_data["judges"]:
        judge = Judge(
            judge_id=judge_data["id"],
            judge_skills=[Sagstype.from_string(skill) for skill in judge_data["skills"]],
            judge_virtual=judge_data["virtual"]
        )
        parsed_data["judges"].append(judge)
    
    # Parse rooms
    for room_data in test_data["rooms"]:
        room = Room(
            room_id=room_data["id"],
            room_virtual=room_data["virtual"]
        )
        parsed_data["rooms"].append(room)
    
    print(f"Generated {len(parsed_data['meetings'])} meetings, "
          f"{len(parsed_data['judges'])} judges, "
          f"{len(parsed_data['rooms'])} rooms")
    
    return parsed_data