from collections import defaultdict

from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.schedule import Schedule
from src.base_model.attribute_enum import Attribute
    
def visualize(schedule: Schedule, view_by="judge"):
    """
    Generate a calendar for the schedule with either judges or rooms displayed as columns.
    
    Args:
        schedule: The Schedule object containing all data
        view_by: Either "judge" or "room" to determine column headers
    """
    judges = schedule.get_all_judges()
    cases = schedule.get_all_cases()
    rooms = schedule.get_all_rooms()
    work_days = schedule.work_days
    timeslot_per_day = schedule.timeslots_per_work_day
    granularity = schedule.granularity
    appointments = schedule.get_all_appointments()
    
    # Determine column entities based on view_by parameter
    if view_by.lower() == "judge":
        column_entities = judges
        entity_ids = sorted([j.judge_id for j in judges])
        entity_name = "Judge"
        entity_id_attr = "judge_id"
        entity_attrs = {judge.judge_id: list(judge.characteristics) for judge in judges}
    elif view_by.lower() == "room":
        column_entities = rooms
        entity_ids = sorted([r.room_id for r in rooms])
        entity_name = "Room"
        entity_id_attr = "room_id"
        entity_attrs = {room.room_id: list(room.characteristics) for room in rooms}
    else:
        raise ValueError("view_by must be either 'judge' or 'room'")
    
    # Group appointments by day
    appointments_by_day = defaultdict(list)
    for app in appointments:
        appointments_by_day[app.day].append(app)
    
    # For each day, create a calendar view
    for day in range(1, work_days + 1):
        print(f"Day {day}:")
        
        # Calculate table width based on number of entities
        col_width = 18  # Width for each column
        
        # Print header separator
        header_line = "+" + "+".join(["-" * col_width for _ in range(len(entity_ids) + 1)]) + "+"
        print(header_line)
        
        # Print header with entity IDs
        print("|" + f"{'Time':^{col_width}}" + "|", end="")
        for entity_id in entity_ids:
            print(f"{entity_name + ' ' + str(entity_id):^{col_width}}" + "|", end="")
        print()
        
        # Find maximum number of characteristics
        max_attrs = max(len(attrs) for attrs in entity_attrs.values())
        
        # Print one attribute per line for each entity
        for i in range(max_attrs):
            print("|" + f"{'':{col_width}}" + "|", end="")
            for entity_id in entity_ids:
                attrs = entity_attrs[entity_id]
                attr_text = str(attrs[i]) if i < len(attrs) else ""
                print(f"{attr_text:^{col_width}}" + "|", end="")
            print()
        
        # Print separator between header and calendar
        print(header_line)
        
        # Create a grid to represent the calendar
        calendar_grid = {}
        
        if day in appointments_by_day:
            # Sort appointments by entity and timeslot for sequential processing
            if view_by.lower() == "judge":
                day_appointments = sorted(appointments_by_day[day], 
                                        key=lambda a: (a.judge.judge_id, a.timeslot_in_day))
            else:  # view_by == "room"
                day_appointments = sorted(appointments_by_day[day], 
                                        key=lambda a: (a.room.room_id, a.timeslot_in_day))
            
            # Track previous appointment for continuation checking
            prev_app = {}  # Track by entity_id
            
            for app in day_appointments:
                timeslot = app.timeslot_in_day
                
                # Get the entity ID based on view_by
                if view_by.lower() == "judge":
                    entity_id = app.judge.judge_id
                    other_entity_str = f"R{app.room.room_id}:{print_room_info(rooms, app.room.room_id)}"
                else:  # view_by == "room"
                    entity_id = app.room.room_id
                    other_entity_str = f"J{app.judge.judge_id}"
                
                # Check if this is a continuation of previous appointment
                is_continuation = False
                if entity_id in prev_app:
                    prev_timeslot = prev_app[entity_id].timeslot_in_day
                    prev_app_entity = prev_app[entity_id]
                    
                    # Compare with previous appointment
                    if (prev_app_entity.meeting.meeting_id == app.meeting.meeting_id and
                        (view_by.lower() == "judge" and prev_app_entity.room.room_id == app.room.room_id or
                         view_by.lower() == "room" and prev_app_entity.judge.judge_id == app.judge.judge_id) and
                        (prev_timeslot + 1 == timeslot or  # Sequential within day
                        (prev_timeslot == timeslot_per_day - 1 and timeslot == 1))):  # Day boundary
                        is_continuation = True
                
                if is_continuation:
                    calendar_grid[(timeslot, entity_id)] = "#############"
                else:
                    calendar_grid[(timeslot, entity_id)] = f"C{app.meeting.case.case_id}/M{app.meeting.meeting_id}:{print_case_info(cases, app.meeting.case.case_id)}/{other_entity_str}"
                
                # Update previous appointment
                prev_app[entity_id] = app
                    
        # Print each timeslot row
        for timeslot in range(1, timeslot_per_day + 1):
            # Calculate time string - starting at 08:30
            base_minutes = 8 * 60 + 30  # 8:30 AM
            total_minutes = base_minutes + ((timeslot - 1) * granularity)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            time_str = f"{hours:02d}:{minutes:02d}"
            
            # Print time and appointment cells
            print("|" + f"{time_str:^{col_width}}" + "|", end="")
            
            for entity_id in entity_ids:
                cell_content = calendar_grid.get((timeslot, entity_id), "")
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
