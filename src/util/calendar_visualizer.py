from collections import defaultdict

from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.schedule import Schedule
from src.base_model.attribute_enum import Attribute
    
def generate_calendar(schedule: Schedule):
    """
    Generate a calendar for the schedule with all judges displayed
    and appointments shown as Case/Room with continuation markers.
    """
    judges: list = schedule.get_all_judges()
    cases: list = schedule.get_all_cases()
    rooms: list = schedule.get_all_rooms()
    work_days = schedule.work_days
    timeslot_per_day = schedule.timeslots_per_work_day
    granularity = schedule.granularity
    appointments = schedule.appointments
    
    # Get all judges, sorted by ID
    all_judge_ids = sorted([j.judge_id for j in judges])
    
    # Group appointments by day
    appointments_by_day = defaultdict(list)
    for app in appointments:
        appointments_by_day[app.day].append(app)
    
    # For each day, create a calendar view
    for day in range(work_days):
        print(f"Day {day + 1}:")
        
        # Calculate table width based on number of judges
        col_width = 18  # Width for each column
        
        # Print header separator
        header_line = "+" + "+".join(["-" * col_width for _ in range(len(all_judge_ids) + 1)]) + "+"
        print(header_line)
        
        # Print header with judge IDs
        print("|" + f"{'Time':^{col_width}}" + "|", end="")
        for judge_id in all_judge_ids:
            print(f"{'Judge ' + str(judge_id):^{col_width}}" + "|", end="")
        print()
        
        # Convert characteristics sets to lists and find maximum number of characteristics
        judge_attrs = {judge.judge_id: list(judge.characteristics) for judge in judges}
        max_attrs = max(len(attrs) for attrs in judge_attrs.values())
        
        # Print one attribute per line for each judge
        for i in range(max_attrs):
            print("|" + f"{'':{col_width}}" + "|", end="")
            for judge_id in all_judge_ids:
                attrs = judge_attrs[judge_id]
                attr_text = str(attrs[i]) if i < len(attrs) else ""
                print(f"{attr_text:^{col_width}}" + "|", end="")
            print()
        
        # Print separator between header and calendar
        print(header_line)
        
        # Create a grid to represent the calendar
        calendar_grid = {}
        
        if day in appointments_by_day:
            # Sort appointments by judge and timeslot for sequential processing
            day_appointments = sorted(appointments_by_day[day], 
                                    key=lambda a: (a.judge.judge_id, a.timeslot_start))
            
            # Track previous appointment for comparison
            prev_app = None
            
            for app in day_appointments:
                timeslot = app.timeslot_start % timeslot_per_day
                judge_id = app.judge.judge_id
                
                # Check if this is a continuation of previous appointment
                is_continuation = False
                if prev_app:
                    prev_timeslot = prev_app.timeslot_start % timeslot_per_day
                    # Check if adjacent timeslot with same judge, case, and room
                    if (prev_app.judge.judge_id == judge_id and
                        prev_app.case.case_id == app.case.case_id and
                        prev_app.room.room_id == app.room.room_id and
                        (prev_timeslot + 1 == timeslot or  # Sequential within day
                        (prev_timeslot == timeslot_per_day - 1 and timeslot == 0))):  # Day boundary
                        is_continuation = True
                
                if is_continuation:
                    calendar_grid[(timeslot, judge_id)] = "#############"
                else:
                    calendar_grid[(timeslot, judge_id)] = f"C{app.case.case_id}:{print_case_info(cases, app.case.case_id)}/R{app.room.room_id}:{print_room_info(rooms, app.room.room_id)}"
                
                # Update previous appointment
                prev_app = app
            
            # meeting_blocks = defaultdict(list)
            # for app in appointments_by_day[day]:
            #     key = (app.case.case_id, app.judge.judge_id, app.room.room_id)
            #     meeting_blocks[key].append(app)
            
            # # Process each meeting block
            # for (case_id, judge_id, room_id), apps in meeting_blocks.items():
            #     # Sort by timeslot
            #     apps.sort(key=lambda a: a.timeslot_start)
                
            #     # Find all timeslots for this meeting
            #     all_timeslots = set()
            #     for app in apps:
            #         timeslot = app.timeslot_start % timeslot_per_day
            #         all_timeslots.add(timeslot)
                
            #     # Find the starting timeslot (lowest)
            #     start_timeslot = min(all_timeslots)
                
            #     # Mark the starting slot with the case/room identifier
            #     calendar_grid[(start_timeslot, judge_id)] = f"C{case_id}:{print_case_info(case_id)}/R{room_id}:{print_room_info(room_id)}"
                
            #     # Mark all other slots of this meeting with continuation markers
            #     for timeslot in all_timeslots:
            #         if timeslot != start_timeslot:
            #             calendar_grid[(timeslot, judge_id)] = "#############"
                    
        # Print each timeslot row
        for timeslot in range(timeslot_per_day):
            # Calculate time string - starting at 08:30
            base_minutes = 8 * 60 + 30  # 8:30 AM
            total_minutes = base_minutes + (timeslot * granularity)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            time_str = f"{hours:02d}:{minutes:02d}"
            
            # Print time and appointment cells with proper centering and borders
            print("|" + f"{time_str:^{col_width}}" + "|", end="")
            
            for judge_id in all_judge_ids:
                cell_content = calendar_grid.get((timeslot, judge_id), "")
                print(f"{cell_content:^{col_width}}" + "|", end="")
            print()
        
        # Print footer separator
        print(header_line)
        print()  # Add empty line between days
        
def print_case_info(cases: list[Case], case_id):
    """Returns a string with abbreviated characteristics of the case"""
    # Find the case with matching ID
    case = None
    for c in cases:
        if c.case_id == case_id:
            case = c
            break
    
    if not case.characteristics:
        return ""  # Fallback if no characteristics
    
    abbr = []
    for attr in case.characteristics:
        # Compare each attribute to the enum values
        if attr == Attribute.STRAFFE:
            abbr.append("S")
        elif attr == Attribute.GRUNDLOV:
            abbr.append("G")
        elif attr == Attribute.DOEDSBO:
            abbr.append("D")
        elif attr == Attribute.TVANG:
            abbr.append("T")
        elif attr == Attribute.CIVIL:
            abbr.append("C")
        elif attr == Attribute.SHORTDURATION:
            abbr.append("Sh")
        elif attr == Attribute.VIRTUAL:
            abbr.append("V")
    
    return "".join(abbr) if abbr else ""

def print_room_info(rooms: list[Room], room_id):
    """Returns a string with abbreviated characteristics of the room"""
    # Find the room with matching ID
    room = None
    for r in rooms:
        if r.room_id == room_id:
            room = r
            break
    
    if not room.characteristics:
        return ""

    abbr = []
    for attr in room.characteristics:
        if attr == Attribute.VIRTUAL:
            abbr.append("V")
        elif attr == Attribute.SECURITY:
            abbr.append("Sc")
        elif attr == Attribute.ACCESSIBILITY:
            abbr.append("A")
    return "".join(abbr) if abbr else ""
