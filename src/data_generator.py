import random
import math
import json
from typing import Dict, Any, List

from src.model import Case, Judge, Room, Attribute, case_judge_compatible, case_room_compatible, judge_room_compatible

class TruncatedNormalDistribution:
    """Generates a truncated normal distribution for case durations."""
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


def generate_test_data(n_cases: int, n_judges: int, n_rooms: int, 
                       work_days: int = 5, granularity: int = 15, 
                       min_per_work_day: int = 480, fixed_duration: bool = False) -> Dict[str, Any]:
    """Generate test data for court scheduling."""
    # Initialize random generator
    gen = random.Random()
    
    # Create duration distribution
    duration_dist = TruncatedNormalDistribution(30.0, 80.0, 5.0, 360.0)
    
    # Get all possible case types (excluding VIRTUAL/PHYSICAL/SHORTDURATION which are handled separately)
    case_types = [attr for attr in list(Attribute) 
                  if attr not in [Attribute.VIRTUAL, 
                                  Attribute.SHORTDURATION, Attribute.SECURITY, 
                                  Attribute.ACCESSIBILITY]]
    
    # Generate cases
    cases = []
    for i in range(1, n_cases + 1):
        if fixed_duration:
            duration = granularity
        else:
            # Generate duration and round to nearest 5
            raw_duration = duration_dist(gen)
            duration = round(raw_duration / 5.0) * 5
        
        # Generate random case type from the filtered list
        case_type = random.choice(case_types)
        
        # Determine if case is virtual (25% chance)
        is_virtual = bool(gen.randint(0, 3) == 0)
        
        # Determine if case needs security (10% chance)
        needs_security = bool(gen.randint(0, 9) == 0)
        
        # Generate case data structure
        case = {
            "id": i,
            "duration": duration,
            "type": str(case_type),
            "virtual": is_virtual,
            "security": needs_security
        }
        cases.append(case)
    
    # Generate judges
    judges = []
    # Track which case types have been covered
    covered_types = set()

    for i in range(1, n_judges + 1):
        # Filter out non-case type attributes
        all_types = case_types.copy()
        
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
        
        # Determine if judge is virtual (25% chance)
        is_virtual = bool(gen.randint(0, 3) == 0)
        
        # Determine if judge requires accessibility (10% chance)
        needs_accessibility = bool(gen.randint(0, 9) == 0)
        
        # Determine if judge has health limitations (shortduration) (15% chance)
        has_health_limits = bool(gen.randint(0, 6) == 0)
        
        # Generate judge
        judge = {
            "id": i,
            "skills": [str(skill) for skill in skills],
            "virtual": is_virtual,
            "accessibility": needs_accessibility,
            "shortduration": has_health_limits
        }
        judges.append(judge)
    
    # Generate rooms
    rooms = []
    for i in range(1, n_rooms + 1):
        # Determine if room is virtual (25% chance)
        is_virtual = bool(gen.randint(0, 3) == 0)
        
        # Determine if room has accessibility (30% chance for physical rooms)
        has_accessibility = bool(not is_virtual and gen.randint(0, 2) == 0)
        
        # Determine if room has security features (20% chance for physical rooms)
        has_security = bool(not is_virtual and gen.randint(0, 4) == 0)
        
        room = {
            "id": i,
            "virtual": is_virtual,
            "accessibility": has_accessibility,
            "security": has_security
        }
        rooms.append(room)
    
    # Create final data structure
    data = {
        "work_days": work_days,
        "min_per_work_day": min_per_work_day,
        "granularity": granularity,
        "cases": cases,
        "judges": judges,
        "rooms": rooms
    }
    
    # Save test data to a file for reference (optional)
    with open('sample_input.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    return data

def generate_test_data_parsed(n_cases: int, n_judges: int, n_rooms: int, 
                             work_days: int = 5, granularity: int = 15, 
                             min_per_work_day: int = 480) -> Dict:
    """Generate and parse test data into model objects."""
    # Generate raw test data
    test_data = generate_test_data(n_cases, n_judges, n_rooms, 
                                  work_days, granularity, min_per_work_day)
    
    # Parse the data into model objects
    parsed_data = {
        "work_days": test_data["work_days"],
        "min_per_work_day": test_data["min_per_work_day"],
        "granularity": test_data["granularity"],
        "cases": [],
        "judges": [],
        "rooms": []
    }

     # Parse judges
    for judge_data in test_data["judges"]:
        skills = [Attribute.from_string(skill) for skill in judge_data["skills"]]
        characteristics = set(skills)
        case_requirements = set()
        room_requirements = set()
        
        # Add virtual or physical characteristic based on the virtual flag
        if judge_data["virtual"]:
            characteristics.add(Attribute.VIRTUAL)
            
        # Add accessibility requirement if needed
        if judge_data.get("accessibility", False):
            characteristics.add(Attribute.ACCESSIBILITY)
            room_requirements.add(Attribute.ACCESSIBILITY)
            
        # Add shortduration requirement if judge has health limitations
        if judge_data.get("shortduration", False):
            characteristics.add(Attribute.SHORTDURATION)
            case_requirements.add(Attribute.SHORTDURATION)
            
        judge = Judge(
            judge_id=judge_data["id"],
            characteristics=characteristics,
            case_requirements=case_requirements,
            room_requirements=room_requirements
        )

        parsed_data["judges"].append(judge)
    
    # Parse cases (cases)
    for case_data in test_data["cases"]:
        case_attr = Attribute.from_string(case_data["type"])
        characteristics = {case_attr}
        judge_requirements = {case_attr}  # Judge must have this skill
        room_requirements = set()  # Default no special room requirements
        
        # Add virtual or physical characteristic based on the virtual flag
        if case_data["virtual"]:
            characteristics.add(Attribute.VIRTUAL)
            judge_requirements.add(Attribute.VIRTUAL)
            room_requirements.add(Attribute.VIRTUAL)
            
        # Add security requirements if needed
        if case_data.get("security", False):
            characteristics.add(Attribute.SECURITY)
            room_requirements.add(Attribute.SECURITY)
            
        # Add SHORTDURATION if case is short (<120 min)
        if case_data["duration"] < 120:
            characteristics.add(Attribute.SHORTDURATION)
            
        case = Case(
            case_id=case_data["id"],
            case_duration=case_data["duration"],
            characteristics=characteristics,
            judge_requirements=judge_requirements,
            room_requirements=room_requirements
        )

        compatible = False
        for judge in parsed_data["judges"]:
            if case_judge_compatible(case, judge):
                compatible = True
                break


        if not compatible:
            suitable_judges: list[Judge] = [j for j in parsed_data["judges"] if isinstance(j, Judge) and case_attr in j.characteristics]
            if not suitable_judges:
                suitable_judges = parsed_data["judges"]
            
            suitable_judge: Judge = suitable_judges[0]  # Pick the first suitable judge

            for requirement in case.judge_requirements:
                if requirement not in suitable_judge.characteristics:
                    suitable_judge.characteristics.add(requirement)

            for requirement in suitable_judge.case_requirements:
                if requirement not in case.characteristics:
                    if requirement == Attribute.SHORTDURATION:
                        case.case_duration = case.case_duration - (case.case_duration - 120)
                        case.characteristics.add(requirement)

        parsed_data["cases"].append(case)
    
   
    # Parse rooms
    for room_data in test_data["rooms"]:
        characteristics = set()
        case_requirements = set()
        judge_requirements = set()
        
        # Add virtual or physical characteristic based on the virtual flag
        if room_data["virtual"]:
            characteristics.add(Attribute.VIRTUAL)
            case_requirements.add(Attribute.VIRTUAL)
            judge_requirements.add(Attribute.VIRTUAL)
            
        # Add accessibility if room has it
        if room_data.get("accessibility", False):
            characteristics.add(Attribute.ACCESSIBILITY)
            
        # Add security if room has it
        if room_data.get("security", False):
            characteristics.add(Attribute.SECURITY)
            
        room = Room(
            room_id=room_data["id"],
            characteristics=characteristics,
            case_requirements=case_requirements,
            judge_requirements=judge_requirements
        )

        parsed_data["rooms"].append(room)

    
    print(f"Generated {len(parsed_data['cases'])} cases, "
          f"{len(parsed_data['judges'])} judges, "
          f"{len(parsed_data['rooms'])} rooms")
    
    return parsed_data