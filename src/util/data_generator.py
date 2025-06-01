import random
import json
import math
from typing import Dict, Any, List, Tuple

from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.attribute_enum import Attribute
from src.base_model.compatibility_checks import case_judge_compatible, case_room_compatible, judge_room_compatible
from src.construction.graph.graph import MeetingJudgeNode
from src.base_model.meeting import Meeting

def return_all_sagstyper() -> list:
    """Return all case types as a list of Attributes"""
    return [
        Attribute.CIVIL,
        Attribute.STRAFFE,
        Attribute.TVANG,
        Attribute.DOEDSBO,
        Attribute.GRUNDLOV
    ]

def generate_test_data(n_cases: int, 
                       work_days: int, granularity: int, 
                       min_per_work_day: int) -> Dict[str, Any]:
    """Generate test data for court scheduling."""
    # Initialize random generator
    gen = random.Random(13062025) # With a fix a seed for reproducibility    

    # Define area probabilities
    area_probabilities = {
        "CIVIL_OMRAADE": 0.043,
        "STRAFFE_OMRAADE": 0.753,
        "TVANG_OMRAADE": 0.023,
        "GRUNDLOV_OMRAADE": 0.166,
        "SKIFTE_OMRAADE": 0.018  # DOEDSBO
    }
    
    # Map areas to case types (from paste-2.txt)
    area_to_case_types = {
        "CIVIL_OMRAADE": [
            "ALMINDELIGE_SMAASAGER_UNDER_50_000_KR", "BOLIGRETSSAG", "CIVILE_SAGER", 
            "FADERSKABSSAG", "SMAA_SMAASAGER_UNDER_5_000_KR", "BERAMMELSESFRI", 
            "BLOKERING", "FORBEREDELSE", "AEGTESKABSSAG", "BOERNEBORTFOERELSE", 
            "BOPAELSSAG", "FADERSKABSSAG_FAMILLIE", "FAMILIERETLIGE_SAGER", 
            "FORAELDREANSVARSSAGER", "NAVNESAG", "PROEVELSESSAG", "SAMVAERSSSAG", 
            "TELEFONMOEDER_I_FAMILIERETLIGE_SAGER", "TVANGSFULDBYRDELSESSAG"
        ],
        "STRAFFE_OMRAADE": [
            "BESKIKKELSESSAGER_BESKIKKELSE", "BESKIKKELSESSAGER_RAADIGHEDSVAGT", 
            "BESKIKKELSESSAGER_SALAER", "DIVERSE_ANDET", "DIVERSE_SUBSIDIAER_ANTICIPERET", 
            "DIVERSE_UDLAENDINGE", "OEVRIGE_STRAFFESAGER_AENDRING_AF_BETINGET_DOM_FORANSTALTNING", 
            "OEVRIGE_STRAFFESAGER_ERSTATNING_M_DOMSMAEND", "OEVRIGE_STRAFFESAGER_ERSTATNING_U_DOMSMAEND", 
            "OEVRIGE_STRAFFESAGER_FORVANDLINGSSTRAF", "SAGER_MED_LAEGDOMMERE_ALMINDELIGE", 
            "SAGER_MED_LAEGDOMMERE_FAERDSEL", "SAGER_MED_LAEGDOMMERE_NAEVNINGESAGER", 
            "SAGER_UDEN_LAEGDOMMERE_BOEDE", "SAGER_UDEN_LAEGDOMMERE_FAERDSEL", 
            "SAGER_UDEN_LAEGDOMMERE_FORUDBERAMMEDE", "SAGER_UDEN_LAEGDOMMERE_SAERLOV_PGF_898", 
            "SAGER_UDEN_LAEGDOMMERE_SPECIELLE_NARKO", "SAGER_UDEN_LAEGDOMMERE_SPIRITUS_NARKO", 
            "SAGER_UDEN_LAEGGDOMMERE_OEVRIGE", "TILSTAAELSESSAGER_ALMINDELIGE", 
            "TILSTAAELSESSAGER_TILTALEFRAFALD_UNGDOMSKONTRAKT", "TILSTAAELSESSAGER_UBETINGET_SPIRITUS_NARKO"
        ],
        "TVANG_OMRAADE": [
            "FOGEDSAGER_JURIST", "FOGEDSAGER_SAGSBEHANDLER", "TVANGSAUKTIONER", 
            "INSOLVENS_DIVERSE", "INSOLVENS_FORBYGGENDE_REKONSTRUKTION", 
            "INSOLVENS_GAELDSSANERING", "INSOLVENS_GRANSKNING", "INSOLVENS_KONKURS", 
            "INSOLVENS_REKONSTRUKTION", "INSOLVENS_SUBSIDIAER_AFHOERING", "INSOLVENS_TVANG"
        ],
        "GRUNDLOV_OMRAADE": [
            "GRUNDLOVSSAGER_MV_ALMINDELIGE", "GRUNDLOVSSAGER_MV_FORANSTALTNING_UNDER_EFTERFORSKNING", 
            "GRUNDLOVSSAGER_MV_UDLAENDINGE"
        ],
        "SKIFTE_OMRAADE": [
            "AEGTEFAELLE_SKIFTE", "DOEDSBO_DOEDSANMELDELSE", "DOEDSBO_SKIFTE_AF_USKIFTET_BO"
        ]
    }
    
    # Case type probabilities and durations (from paste-3.txt)
    case_type_data = {
        "AEGTEFAELLE_SKIFTE": {"prob": 0.013470, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "AEGTESKABSSAG": {"prob": 0.002010, "durations": [(60, 1.0)]},
        "ALMINDELIGE_SMAASAGER_UNDER_50_000_KR": {"prob": 0.100523, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "BERAMMELSESFRI": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "BESKIKKELSESSAGER_BESKIKKELSE": {"prob": 0.010052, "durations": [(30, 0.4), (60, 0.4), (90, 0.2)]},
        "BESKIKKELSESSAGER_RAADIGHEDSVAGT": {"prob": 0.000201, "durations": [(30, 1.0)]},
        "BESKIKKELSESSAGER_SALAER": {"prob": 0.004021, "durations": [(30, 1.0)]},
        "BLOKERING": {"prob": 0.000000, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "BOERNEBORTFOERELSE": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "BOLIGRETSSAG": {"prob": 0.030157, "durations": [(240, 0.9), (300, 0.1)]},
        "BOPAELSSAG": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "CIVILE_SAGER": {"prob": 0.002010, "durations": [(240, 0.9), (300, 0.1)]},
        "DIVERSE_ANDET": {"prob": 0.002010, "durations": [(60, 0.75), (90, 0.2), (120, 0.05)]},
        "DIVERSE_SUBSIDIAER_ANTICIPERET": {"prob": 0.002010, "durations": [(60, 0.75), (90, 0.2), (120, 0.05)]},
        "DIVERSE_UDLAENDINGE": {"prob": 0.020105, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "DOEDSBO_DOEDSANMELDELSE": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "DOEDSBO_SKIFTE_AF_USKIFTET_BO": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "FADERSKABSSAG": {"prob": 0.006594, "durations": [(30, 0.1), (60, 0.8), (90, 0.1)]},
        "FADERSKABSSAG_FAMILLIE": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "FAMILIERETLIGE_SAGER": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "FOGEDSAGER_JURIST": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "FOGEDSAGER_SAGSBEHANDLER": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "FORAELDREANSVARSSAGER": {"prob": 0.002010, "durations": [(120, 0.1), (180, 0.8), (240, 0.1)]},
        "FORBEREDELSE": {"prob": 0.000000, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "GRUNDLOVSSAGER_MV_ALMINDELIGE": {"prob": 0.020105, "durations": [(60, 0.05), (90, 0.15), (120, 0.35), (180, 0.25), (240, 0.1), (300, 0.05), (360, 0.05)]},
        "GRUNDLOVSSAGER_MV_FORANSTALTNING_UNDER_EFTERFORSKNING": {"prob": 0.020105, "durations": [(30, 0.6), (60, 0.25), (90, 0.1), (120, 0.05)]},
        "GRUNDLOVSSAGER_MV_UDLAENDINGE": {"prob": 0.002010, "durations": [(30, 0.7), (60, 0.2), (90, 0.1)]},
        "INSOLVENS_DIVERSE": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "INSOLVENS_FORBYGGENDE_REKONSTRUKTION": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "INSOLVENS_GAELDSSANERING": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "INSOLVENS_GRANSKNING": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "INSOLVENS_KONKURS": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "INSOLVENS_REKONSTRUKTION": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "INSOLVENS_SUBSIDIAER_AFHOERING": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "INSOLVENS_TVANG": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "NAVNESAG": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "OEVRIGE_STRAFFESAGER_AENDRING_AF_BETINGET_DOM_FORANSTALTNING": {"prob": 0.002010, "durations": [(30, 0.05), (60, 0.5), (90, 0.4), (120, 0.05)]},
        "OEVRIGE_STRAFFESAGER_ERSTATNING_M_DOMSMAEND": {"prob": 0.020105, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "OEVRIGE_STRAFFESAGER_ERSTATNING_U_DOMSMAEND": {"prob": 0.002010, "durations": [(90, 0.1), (120, 0.65), (150, 0.2), (180, 0.05)]},
        "OEVRIGE_STRAFFESAGER_FORVANDLINGSSTRAF": {"prob": 0.002010, "durations": [(60, 0.4), (90, 0.4), (120, 0.2)]},
        "PROEVELSESSAG": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "SAGER_MED_LAEGDOMMERE_ALMINDELIGE": {"prob": 0.201045, "durations": [(90, 0.445), (268, 0.342), (534, 0.14), (877, 0.04), (1391, 0.022), (2261, 0.007), (3140, 0.001)]},
        "SAGER_MED_LAEGDOMMERE_FAERDSEL": {"prob": 0.020105, "durations": [(90, 0.15), (120, 0.6), (150, 0.15), (180, 0.1)]},
        "SAGER_MED_LAEGDOMMERE_NAEVNINGESAGER": {"prob": 0.005428, "durations": [(102, 0.056), (648, 0.056), (928, 0.101), (1418, 0.279), (2360, 0.223), (3038, 0.057)]},
        "SAGER_UDEN_LAEGDOMMERE_BOEDE": {"prob": 0.211098, "durations": [(30, 0.6), (45, 0.3), (60, 0.1)]},
        "SAGER_UDEN_LAEGDOMMERE_FAERDSEL": {"prob": 0.020105, "durations": [(30, 0.7), (60, 0.1), (90, 0.05), (120, 0.05), (150, 0.05), (180, 0.05)]},
        "SAGER_UDEN_LAEGDOMMERE_FORUDBERAMMEDE": {"prob": 0.001709, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "SAGER_UDEN_LAEGDOMMERE_SAERLOV_PGF_898": {"prob": 0.100523, "durations": [(150, 0.4), (180, 0.4), (300, 0.18), (600, 0.02)]},
        "SAGER_UDEN_LAEGDOMMERE_SPECIELLE_NARKO": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "SAGER_UDEN_LAEGDOMMERE_SPIRITUS_NARKO": {"prob": 0.002010, "durations": [(30, 0.5), (60, 0.35), (90, 0.05), (120, 0.05), (150, 0.03), (180, 0.02)]},
        "SAGER_UDEN_LAEGGDOMMERE_OEVRIGE": {"prob": 0.002010, "durations": [(30, 0.5), (60, 0.35), (90, 0.05), (120, 0.05), (150, 0.03), (180, 0.02)]},
        "SAMVAERSSSAG": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "SMAA_SMAASAGER_UNDER_5_000_KR": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "TELEFONMOEDER_I_FAMILIERETLIGE_SAGER": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "TILSTAAELSESSAGER_ALMINDELIGE": {"prob": 0.120627, "durations": [(30, 0.8), (60, 0.1), (90, 0.05), (120, 0.03), (150, 0.02)]},
        "TILSTAAELSESSAGER_TILTALEFRAFALD_UNGDOMSKONTRAKT": {"prob": 0.000040, "durations": [(30, 1.0)]},
        "TILSTAAELSESSAGER_UBETINGET_SPIRITUS_NARKO": {"prob": 0.001508, "durations": [(30, 0.8), (60, 0.13), (90, 0.07)]},
        "TVANGSAUKTIONER": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]},
        "TVANGSFULDBYRDELSESSAG": {"prob": 0.002010, "durations": [(30, 0.2), (60, 0.5), (90, 0.2), (120, 0.1)]}
    }
    
    # Map from area to the corresponding attribute
    area_to_attribute = {
        "CIVIL_OMRAADE": Attribute.CIVIL,
        "STRAFFE_OMRAADE": Attribute.STRAFFE,
        "TVANG_OMRAADE": Attribute.TVANG,
        "GRUNDLOV_OMRAADE": Attribute.GRUNDLOV,
        "SKIFTE_OMRAADE": Attribute.DOEDSBO
    }
    
    # Generate cases
    cases = []
    meeting_counter = 1
    timeslots_per_day = min_per_work_day // granularity
    max_minutes_per_day = timeslots_per_day * granularity
    
    for i in range(1, n_cases + 1):
        # Step 1: Select case area based on probabilities
        area = gen.choices(
            list(area_probabilities.keys()),
            weights=list(area_probabilities.values()),
            k=1
        )[0]
        
        # Step 2: Select a specific case type from that area
        # Calculate normalized probabilities within area
        area_case_types = area_to_case_types[area]
        type_probs = []
        
        for case_type in area_case_types:
            if case_type in case_type_data:
                type_probs.append(case_type_data[case_type]["prob"])
            else:
                type_probs.append(0.001)  # Default small probability
        
        # Normalize probabilities 
        total_prob = sum(type_probs)
        if total_prob > 0:
            type_probs = [p/total_prob for p in type_probs]
        
        case_type = gen.choices(area_case_types, weights=type_probs, k=1)[0]
        
        if case_type in case_type_data:
            duration_distribution = case_type_data[case_type]["durations"]
            durations, probs = zip(*duration_distribution)
            raw_duration = gen.choices(durations, weights=probs, k=1)[0]
        else:
            # Default duration if not found
            raw_duration = gen.choice([30, 60, 90, 120])

        # Round up to the nearest multiple of granularity
        duration = math.ceil(raw_duration / granularity) * granularity
        
        # Determine if case is virtual (5% chance)
        is_virtual = bool(gen.randint(0, 20) == 0)
        
        # Determine if case needs security (5% chance for non-virtual cases)
        needs_security = bool(not is_virtual and gen.randint(0, 20) == 0)
        
        # Split into multiple meetings if needed
        # Split into multiple meetings if needed
        meetings = []
        remaining_duration = duration

        if duration > max_minutes_per_day:
            # First meeting uses a full day
            meetings.append({
                "id": meeting_counter,
                "duration": max_minutes_per_day
            })
            meeting_counter += 1
            remaining_duration -= max_minutes_per_day
            
            # Split remaining duration into additional meetings
            while remaining_duration > 0:
                next_meeting_duration = min(remaining_duration, max_minutes_per_day)
                # Ensure duration is a multiple of granularity
                next_meeting_duration = math.ceil(next_meeting_duration / granularity) * granularity
                
                # Handle edge case where rounding might exceed remaining duration
                if next_meeting_duration > remaining_duration:
                    next_meeting_duration = math.floor(remaining_duration / granularity) * granularity
                    if next_meeting_duration == 0:
                        next_meeting_duration = granularity
                
                meetings.append({
                    "id": meeting_counter,
                    "duration": next_meeting_duration
                })
                meeting_counter += 1
                remaining_duration -= next_meeting_duration
        else:
            # Case fits in a single meeting
            meetings.append({
                "id": meeting_counter,
                "duration": duration
            })
            meeting_counter += 1
        
        # Generate case data structure
        case = {
            "id": i,
            "duration": duration,
            "type": area_to_attribute[area].name,  # Convert area to attribute name
            "virtual": is_virtual,
            "security": needs_security,
            "meetings": meetings,
            "original_type": case_type  # Keep track of original case type for reference
        }
        cases.append(case)
    
    # Create final data structure
    data = {
        "work_days": work_days,
        "min_per_work_day": min_per_work_day,
        "granularity": granularity,
        "cases": cases,
    }
    
    # Save test data to a file for reference (optional)
    with open('sample_input.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    return data

def generate_test_data_parsed(n_cases: int, 
                             work_days: int, granularity: int, 
                             min_per_work_day: int) -> Dict:
    """Generate and parse test data into model objects."""
    # Generate raw test data
    test_data = generate_test_data(n_cases, work_days, granularity, min_per_work_day)
    
    # Parse the data into model objects
    parsed_data = {
        "work_days": test_data["work_days"],
        "min_per_work_day": test_data["min_per_work_day"],
        "granularity": test_data["granularity"],
        "cases": [],
        "judges": [],
        "rooms": []
    }

    all_sagstyper = set(return_all_sagstyper())

            
    judge1 = Judge(
        judge_id=1,
        characteristics=all_sagstyper | {Attribute.SHORTDURATION},
        case_requirements={Attribute.SHORTDURATION},
        room_requirements=set()
    )
    judge2 = Judge(
        judge_id=2,
        characteristics=all_sagstyper | {Attribute.ACCESSIBILITY},
        case_requirements=set(),
        room_requirements={Attribute.ACCESSIBILITY}
    )
    judge3 = Judge(
        judge_id=3,
        characteristics=all_sagstyper | {Attribute.ACCESSIBILITY},
        case_requirements=set(),
        room_requirements={Attribute.ACCESSIBILITY}
    )
    judge4 = Judge(
        judge_id=4,
        characteristics=all_sagstyper,
        case_requirements=set(),
        room_requirements=set()
    )
    judge5 = Judge(
        judge_id=5,
        characteristics=all_sagstyper,
        case_requirements=set(),
        room_requirements=set()
    )
    judge6 = Judge(
        judge_id=6,
        characteristics=all_sagstyper,
        case_requirements=set(),
        room_requirements=set()
    )
    judge7 = Judge(
        judge_id=7,
        characteristics=all_sagstyper,
        case_requirements=set(),
        room_requirements=set()
    )
    judge8 = Judge(
        judge_id=8,
        characteristics=all_sagstyper,   
        case_requirements=set(),
        room_requirements=set()
    )
    judge9 = Judge(
        judge_id=9,
        characteristics={Attribute.STRAFFE, Attribute.GRUNDLOV},
        case_requirements=set(),
        room_requirements=set()
    )
    judge10 = Judge(
        judge_id=10,
        characteristics=all_sagstyper | {Attribute.VIRTUAL},
        case_requirements=set(),
        room_requirements=set()
    )
    all_judges = [judge1, judge2, judge3, judge4, judge5, judge6, judge7, judge8, judge9, judge10]  
    parsed_data["judges"].extend(all_judges)
    
    # Parse cases
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
        if case_data["security"]:
            if not case_data["virtual"]:
                characteristics.add(Attribute.SECURITY)
                room_requirements.add(Attribute.SECURITY)
            
        # Add SHORTDURATION if case is short (<120 min)
        if case_data["duration"] < 120:
            characteristics.add(Attribute.SHORTDURATION)
            
        case = Case(
            case_id=case_data["id"],
            characteristics=characteristics,
            judge_requirements=judge_requirements,
            room_requirements=room_requirements
        )

        # Check for compatibility with at least one judge
        compatible = False
        for judge in parsed_data["judges"]:
            if case_judge_compatible(case, judge):
                compatible = True
                break

        # If no compatible judge, modify a judge to make compatible
        if not compatible:
            suitable_judges = [j for j in parsed_data["judges"] if isinstance(j, Judge) and case_attr in j.characteristics]
            if not suitable_judges:
                suitable_judges = parsed_data["judges"]
            
            suitable_judge = suitable_judges[0]  # Pick the first suitable judge

            for requirement in case.judge_requirements:
                if requirement not in suitable_judge.characteristics:
                    suitable_judge.characteristics.add(requirement)

            for requirement in suitable_judge.case_requirements:
                if requirement not in case.characteristics:
                    if requirement == Attribute.SHORTDURATION:
                        case.characteristics.add(requirement)
        
        # Create meetings for this case
        for meeting_data in case_data["meetings"]:
            meeting = Meeting(
                meeting_id=meeting_data["id"],
                meeting_duration=meeting_data["duration"],
                duration_of_stay=0,
                judge=None,
                room=None,
                case=case
            )
            case.meetings.append(meeting)

        parsed_data["cases"].append(case)
    


    room1 = Room(
        room_id=1,
        characteristics={Attribute.VIRTUAL},
        case_requirements={Attribute.VIRTUAL},
        judge_requirements={Attribute.VIRTUAL}
    )
    room2 = Room(
        room_id=2,
        characteristics={Attribute.VIRTUAL, Attribute.ACCESSIBILITY, Attribute.SECURITY},
        case_requirements=set(),
        judge_requirements=set()
    )
    room3 = Room(
        room_id=3,
        characteristics={Attribute.ACCESSIBILITY, Attribute.SECURITY, Attribute.VIRTUAL},
        case_requirements=set(),
        judge_requirements=set()
    )
    room4 = Room(
        room_id=4,
        characteristics={Attribute.SECURITY},
        case_requirements=set(),
        judge_requirements=set()
    )
    room5 = Room(
        room_id=5,
        characteristics={Attribute.ACCESSIBILITY, Attribute.SECURITY},
        case_requirements=set(),
        judge_requirements=set()
    )
    room6 = Room(
        room_id=6,
        characteristics={Attribute.SECURITY, Attribute.ACCESSIBILITY},
        case_requirements=set(),
        judge_requirements=set()
    )
    room7 = Room(
        room_id=7,
        characteristics={Attribute.SECURITY, Attribute.ACCESSIBILITY},
        case_requirements=set(),
        judge_requirements=set()
    )
    room8 = Room(
        room_id=8,
        characteristics={Attribute.ACCESSIBILITY},
        case_requirements=set(),
        judge_requirements=set()
    )
    room9 = Room(
        room_id=9,
        characteristics=set(),
        case_requirements=set(),
        judge_requirements=set()
    )
    room10 = Room(
        room_id=10,
        characteristics={Attribute.ACCESSIBILITY, Attribute.SECURITY}, 
        case_requirements=set(),
        judge_requirements=set()
    )
    all_rooms = [room1, room2, room3, room4, room5, room6, room7, room8, room9, room10]
    parsed_data["rooms"].extend(all_rooms)
    
    # Ensure necessary attributes are present in at least one room
    attributes_to_ensure = [
        Attribute.VIRTUAL,
        Attribute.ACCESSIBILITY,
        Attribute.SECURITY
    ]

    if parsed_data["rooms"]:
        for attribute_to_check in attributes_to_ensure:
            attribute_found = False
            for room in parsed_data["rooms"]:
                if attribute_to_check in room.characteristics:
                    attribute_found = True
                    break

            if not attribute_found:
                for room_candidate in parsed_data["rooms"]:
                    room_candidate.characteristics.add(attribute_to_check)
                    break

    # Set case reference in meetings
    for case in parsed_data["cases"]:
        for meeting in case.meetings:
            meeting.case = case


    return parsed_data