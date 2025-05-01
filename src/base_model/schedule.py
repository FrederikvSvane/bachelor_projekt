from typing import Dict
from copy import deepcopy

from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.case import Case
from src.base_model.meeting import Meeting
from src.base_model.appointment import Appointment
from src.construction.graph.graph import UndirectedGraph, DirectedGraph, MeetingJudgeRoomNode, construct_conflict_graph

from src.construction.graph.matching import (
    assign_cases_to_judges, assign_meeting_judge_pairs_to_rooms, 
)
from src.construction.graph.coloring import DSatur


class Schedule:
    """Class that manages the court schedule."""
    
    def __init__(self, work_days: int, minutes_in_a_work_day: int = 390, granularity: int = 5, judges: list[Judge] = None, rooms: list[Room] = None, meetings: list[Meeting] = None, cases: list[Case] = None):
        self.appointments_by_day_and_timeslot: dict[int, Dict[int, list[Appointment]]] = {} # the main schedule dictionary. Stores appointments by day and timeslot
        self.appointment_chains: dict[int, list[Appointment]] = {} # dictionary of appointment chains. Key is the meeting ID, value is a list of appointments
        self.unplanned_meetings: list[Meeting] = [] # list of unplanned meetings. Ie meetings that are supposed to be scheduled, but are not yet in the schedule
        self.work_days: int = work_days # Amount of workdays in the schedule / the total length of the schedule. (1-indexed)
        self.minutes_in_a_work_day: int = minutes_in_a_work_day # minutes in a work day (default: 390 min = 6.5 hours)
        self.granularity: int = granularity # how many minutes in a timeslot (default: 5)
        self.timeslots_per_work_day: int = minutes_in_a_work_day // granularity
        self.all_judges: list[Judge] = judges
        self.all_rooms: list[Room] = rooms
        self.all_meetings: list[Meeting] = meetings
        self.all_cases: list[Case] = cases

        # initializing the appointments_by_day_and_timeslot dictionary
        for day in range(1, self.work_days + 1):
            self.appointments_by_day_and_timeslot[day] = {}
            for timeslot in range(1, self.timeslots_per_work_day + 1):
                self.appointments_by_day_and_timeslot[day][timeslot] = []
    
    def __eq__(self, other):


        """Compare two Schedule objects for equality."""
        if not isinstance(other, Schedule):
            raise TypeError(f"Cannot compare Schedule with {type(other).__name__}")
        
        # Compare basic properties
        if self.work_days != other.work_days:
            raise ValueError(f"Work days differ: {self.work_days} vs {other.work_days}")
        if self.minutes_in_a_work_day != other.minutes_in_a_work_day:
            raise ValueError(f"Minutes in work day differ: {self.minutes_in_a_work_day} vs {other.minutes_in_a_work_day}")
        if self.granularity != other.granularity:
            raise ValueError(f"Granularity differs: {self.granularity} vs {other.granularity}")
        if self.timeslots_per_work_day != other.timeslots_per_work_day:
            raise ValueError(f"Timeslots per work day differ: {self.timeslots_per_work_day} vs {other.timeslots_per_work_day}")
        
        # Compare days with appointments
        self_days = set(self.appointments_by_day_and_timeslot.keys())
        other_days = set(other.appointments_by_day_and_timeslot.keys())
        if self_days != other_days:
            missing_in_self = other_days - self_days
            missing_in_other = self_days - other_days
            error_msg = "Days with appointments differ:"
            if missing_in_self:
                error_msg += f" Missing in self: {missing_in_self}."
            if missing_in_other:
                error_msg += f" Missing in other: {missing_in_other}."
            raise ValueError(error_msg)
        
        # Compare unplanned meetings
        for unplanned_meeting in self.unplanned_meetings:
            if unplanned_meeting not in other.unplanned_meetings:
                raise ValueError(f"Unplanned meeting in self missing from other: {unplanned_meeting}")
        
        for other_unplanned_meeting in other.unplanned_meetings:
            if other_unplanned_meeting not in self.unplanned_meetings:
                raise ValueError(f"Unplanned meeting in other missing from self: {other_unplanned_meeting}")
        
        # Compare appointments by day and timeslot
        for day in self_days:
            self_timeslots = set(self.appointments_by_day_and_timeslot[day].keys())
            other_timeslots = set(other.appointments_by_day_and_timeslot[day].keys())
            
            if self_timeslots != other_timeslots:
                missing_in_self = other_timeslots - self_timeslots
                missing_in_other = self_timeslots - other_timeslots
                error_msg = f"Timeslots for day {day} differ:"
                if missing_in_self:
                    error_msg += f" Missing in self: {missing_in_self}."
                if missing_in_other:
                    error_msg += f" Missing in other: {missing_in_other}."
                raise ValueError(error_msg)
            
            for timeslot in self_timeslots:
                self_appointments = set(self.appointments_by_day_and_timeslot[day][timeslot])
                other_appointments = set(other.appointments_by_day_and_timeslot[day][timeslot])
                
                if len(self_appointments) != len(other_appointments):
                    raise ValueError(f"Number of appointments differ for day {day}, timeslot {timeslot}: {len(self_appointments)} vs {len(other_appointments)}")
                
                for app in self.appointments_by_day_and_timeslot[day][timeslot]:
                    if app not in other.appointments_by_day_and_timeslot[day][timeslot]:
                        raise ValueError(f"Appointment in self missing from other at day {day}, timeslot {timeslot}: {app}")
        
        # Compare judges
        if (self.all_judges is None) != (other.all_judges is None):
            raise ValueError(f"Judges: one has judges, the other doesn't. Self: {self.all_judges is not None}, Other: {other.all_judges is not None}")
        
        if self.all_judges is not None:
            if len(self.all_judges) != len(other.all_judges):
                raise ValueError(f"Number of judges differ: {len(self.all_judges)} vs {len(other.all_judges)}")
            
            self_judges_map = {j.judge_id: j for j in self.all_judges}
            other_judges_map = {j.judge_id: j for j in other.all_judges}
            
            if set(self_judges_map.keys()) != set(other_judges_map.keys()):
                missing_in_self = set(other_judges_map.keys()) - set(self_judges_map.keys())
                missing_in_other = set(self_judges_map.keys()) - set(other_judges_map.keys())
                error_msg = "Judge IDs differ:"
                if missing_in_self:
                    error_msg += f" Missing in self: {missing_in_self}."
                if missing_in_other:
                    error_msg += f" Missing in other: {missing_in_other}."
                raise ValueError(error_msg)
            
            for judge_id, judge in self_judges_map.items():
                if judge != other_judges_map[judge_id]:
                    raise ValueError(f"Judge with ID {judge_id} differs: {judge} vs {other_judges_map[judge_id]}")
        
        # Compare rooms
        if (self.all_rooms is None) != (other.all_rooms is None):
            raise ValueError(f"Rooms: one has rooms, the other doesn't. Self: {self.all_rooms is not None}, Other: {other.all_rooms is not None}")
        
        if self.all_rooms is not None:
            if len(self.all_rooms) != len(other.all_rooms):
                raise ValueError(f"Number of rooms differ: {len(self.all_rooms)} vs {len(other.all_rooms)}")
            
            self_rooms_map = {r.room_id: r for r in self.all_rooms}
            other_rooms_map = {r.room_id: r for r in other.all_rooms}
            
            if set(self_rooms_map.keys()) != set(other_rooms_map.keys()):
                missing_in_self = set(other_rooms_map.keys()) - set(self_rooms_map.keys())
                missing_in_other = set(self_rooms_map.keys()) - set(other_rooms_map.keys())
                error_msg = "Room IDs differ:"
                if missing_in_self:
                    error_msg += f" Missing in self: {missing_in_self}."
                if missing_in_other:
                    error_msg += f" Missing in other: {missing_in_other}."
                raise ValueError(error_msg)
            
            for room_id, room in self_rooms_map.items():
                if room != other_rooms_map[room_id]:
                    raise ValueError(f"Room with ID {room_id} differs: {room} vs {other_rooms_map[room_id]}")
        
        return True
    
    def add_meeting_to_schedule(self, appointment: Appointment):
        if appointment.day not in self.appointments_by_day_and_timeslot:
            self.appointments_by_day_and_timeslot[appointment.day] = {}
        if appointment.timeslot_in_day not in self.appointments_by_day_and_timeslot[appointment.day]:
            self.appointments_by_day_and_timeslot[appointment.day][appointment.timeslot_in_day] = []
        self.appointments_by_day_and_timeslot[appointment.day][appointment.timeslot_in_day].append(appointment)


    def initialize_appointment_chains(self) -> None:
        for app in self.iter_appointments():
            if app.meeting.meeting_id not in self.appointment_chains:
                self.appointment_chains[app.meeting.meeting_id] = []
            self.appointment_chains[app.meeting.meeting_id].append(app)
            
        
    
    def add_to_unplanned_meetings(self, meeting: Meeting) -> None:
        if meeting is None:
            raise ValueError("Meeting cannot be None")
        if meeting in self.unplanned_meetings:
            raise ValueError(f"Meeting {meeting} already exists in unplanned meetings")
        else:
            self.unplanned_meetings.append(meeting)

    def pop_meeting_from_unplanned_meetings(self, meeting_id: int) -> Meeting:
        """
        Args:
            meeting_id: The ID of the meeting to retrieve
        Returns:
            The meeting object if found in unplanned meetings
        """
        for i, meeting in enumerate(self.unplanned_meetings):
            if meeting.meeting_id == meeting_id:
                return self.unplanned_meetings.pop(i)

        raise ValueError(f"Meeting with ID {meeting_id} not found in unplanned meetings")
    
    def get_all_unplanned_meetings(self) -> list[Meeting]:
        return self.unplanned_meetings    
    
    def get_all_planned_meetings(self) -> list[Meeting]:
        meetings = []
        meeting_ids = set()
        
        for app in self.iter_appointments():
            if app.meeting.meeting_id not in meeting_ids:
                meeting_ids.add(app.meeting.meeting_id)
                meetings.append(app.meeting)
        return meetings
    
    def get_all_meetings(self) -> list[Meeting]:
        """
        Returns:
            A list of all meetings in the schedule, planned and unplanned
        """
        meetings = self.get_all_planned_meetings()
        meetings.extend(self.unplanned_meetings)
        return meetings
    
    def print_unplanned_meetings(self) -> None:
        if not self.unplanned_meetings:
            print("No unplanned meetings.")
            return

        print("Unplanned meetings:")
        for meeting in self.unplanned_meetings:
            print(f"  {meeting}")
    
    def iter_appointments(self):
        """
        Iterate through all appointments in the schedule
        Use like:
        for app in schedule.iter_appointments():
        """
        for day in range(1, self.work_days + 1):
            if day in self.appointments_by_day_and_timeslot:
                for timeslot in range(1, self.timeslots_per_work_day + 1):
                    if timeslot in self.appointments_by_day_and_timeslot[day]:
                        for app in self.appointments_by_day_and_timeslot[day][timeslot]:
                            yield app

    def get_all_appointments(self) -> list[Appointment]:
        """Return flat list of all appointments"""
        appointments = []
        for day in range(1, self.work_days + 1):
            if day in self.appointments_by_day_and_timeslot:
                for timeslot in range(1, self.timeslots_per_work_day + 1):
                    if timeslot in self.appointments_by_day_and_timeslot[day]:
                        appointments.extend(self.appointments_by_day_and_timeslot[day][timeslot])
        return appointments
            
    def get_all_judges(self) -> list:
        return self.all_judges

    def get_all_rooms(self) -> list:
        return self.all_rooms

    def get_all_meetings(self) -> list:
        return self.all_meetings

    def get_all_cases(self) -> list:
        return self.all_cases

    def get_appointment_chain(self, meeting_id: int) -> list[Appointment]:
        """
        Get the appointment chain for a given meeting.
        """

        if meeting_id not in self.appointment_chains:
            raise ValueError(f"Meeting {meeting_id} not found in appointment chains")
        return self.appointment_chains[meeting_id]
    
    def get_time_from_timeslot(self, timeslot: int) -> str:
        day_timeslot = timeslot % self.timeslots_per_work_day
        minutes = day_timeslot * self.granularity
        hours = minutes // 60
        minutes = minutes % 60
        
        return f"{hours:02d}:{minutes:02d}"
    
    def move_all_dayboundary_violations(self) -> None:
        """
        Move all meetings that cross day boundaries back so they don't cross day boundaries anymore.
        This function doesn't care about conflicts - it simply moves the appointments to ensure
        that all appointments for a given meeting occur within the same day.
        """
        
        chain_dict = self.appointment_chains
        
        for meeting_id, appointments in chain_dict.items():
            if len(appointments) > 1:
                first_day = appointments[0].day
                last_day = appointments[-1].day
                
                if first_day != last_day:
                    meeting_timeslots = len(appointments)
                    last_valid_slot = self.timeslots_per_work_day - meeting_timeslots + 1
                    
                    if last_valid_slot < 1:
                        print(f"  Warning: Meeting {meeting_id} is too long ({meeting_timeslots} timeslots) to fit in a single day ({self.timeslots_per_work_day} timeslots). Starting at timeslot 1.")
                        last_valid_slot = 1
                    
                    for app in appointments:
                        if app.day in self.appointments_by_day_and_timeslot and app.timeslot_in_day in self.appointments_by_day_and_timeslot[app.day]:
                            if app in self.appointments_by_day_and_timeslot[app.day][app.timeslot_in_day]:
                                self.appointments_by_day_and_timeslot[app.day][app.timeslot_in_day].remove(app)
                    
                    for i, app in enumerate(appointments):
                        new_timeslot = last_valid_slot + i
                        app.day = first_day
                        app.timeslot_in_day = new_timeslot
                        
                        if app.day not in self.appointments_by_day_and_timeslot:
                            self.appointments_by_day_and_timeslot[app.day] = {}
                        if app.timeslot_in_day not in self.appointments_by_day_and_timeslot[app.day]:
                            self.appointments_by_day_and_timeslot[app.day][app.timeslot_in_day] = []
                        
                        self.appointments_by_day_and_timeslot[app.day][app.timeslot_in_day].append(app)
    
    def trim_schedule_length_if_possible(self) -> None:
        """
        Checks if the last day of the schedule is empty and removes it if so.
        Continues until a non-empty day is found or only one day remains.
        """
        while self.work_days > 1:
            last_day = self.work_days
            is_empty = True

            if last_day in self.appointments_by_day_and_timeslot:
                for _timeslot, appointments in self.appointments_by_day_and_timeslot[last_day].items():
                    if appointments:
                        is_empty = False
                        break 

            if is_empty:
                #print(f"Trimming empty day {last_day} from schedule.")
                self.work_days -= 1
            else:
                break
        
    
    def to_json(self) -> Dict:
        """
        Convert the schedule to a JSON-serializable dictionary.
        
        Returns:
            A dictionary representing the schedule
        """
        result = {
            "work_days": self.work_days,
            "minutes_in_a_work_day": self.minutes_in_a_work_day,
            "granularity": self.granularity,
            "timeslots_per_work_day": self.timeslots_per_work_day,
            "appointments": []
        }
        appointments: list[Appointment] = self.get_all_appointments()
        for app in appointments:
            appointment_dict = {
                "day": app.day,
                "timeslot_in_day": app.timeslot_in_day,
                "time": self.get_time_from_timeslot(app.timeslot_in_day),
                "meeting": {
                    "id": app.meeting.meeting_id,
                    "duration": app.meeting.meeting_duration,
                    "Attributes": str(app.meeting.case.characteristics),
                },
                "judge": {
                    "id": app.judge.judge_id,
                    "Attributes:": str(app.judge.characteristics),
                },
                "room": {
                    "id": app.room.room_id,
                    "Attributes:": str(app.room.characteristics),
                }
            }
            result["appointments"].append(appointment_dict)
        
        return result

    def generate_schedule_from_colored_graph(self, graph: UndirectedGraph) -> None:
        """
        Generate appointments using the node "color" as timeslot.
        
        Args:
            graph: The colored undirected graph
        """
        
        # For safety, clear the schedule first
        self.appointments_by_day_and_timeslot = {day: {ts: [] for ts in range(1, self.timeslots_per_work_day + 1)} for day in range(1, self.work_days + 1)}
        
        max_color = -1 # tracking the maximum color (timeslot) used
        
        for i in range(graph.get_num_nodes()):
            node = graph.get_node(i) # getting the CaseJudgeRoomNode from the graph
            
            if not isinstance(node, MeetingJudgeRoomNode):
                raise ValueError(f"Node {i} is not a MeetingJudgeRoomNode. Cannot add to schedule. Terminating.")
            
            # Determining the day and timeslot in day based on assigned color
            color = node.get_color()
            if color == -1:
                raise ValueError(f"Node {i} has no color assigned. Cannot add to schedule. Terminating.")
            day = color // self.timeslots_per_work_day + 1
            timeslot_in_day = color % self.timeslots_per_work_day + 1
            max_color = max(max_color, color)            
            
            # Also for safety, initialize empty appointment list for the day and timeslot
            if day not in self.appointments_by_day_and_timeslot:
                self.appointments_by_day_and_timeslot[day] = {}
            if timeslot_in_day not in self.appointments_by_day_and_timeslot[day]:
                self.appointments_by_day_and_timeslot[day][timeslot_in_day] = []

            # Create an appointment
            appointment = Appointment(
                meeting = node.get_meeting(),
                judge = node.get_judge(),
                room = node.get_room(),
                day = day,
                timeslot_in_day = timeslot_in_day,
                )
            
            appointment.meeting.judge = appointment.judge
            appointment.meeting.room = appointment.room
            
            self.appointments_by_day_and_timeslot[day][timeslot_in_day].append(appointment)
            
        # Adjusting the length of the schedule based on amount of days used
        max_day_used = max_color // self.timeslots_per_work_day + 1
        old_work_days = self.work_days
        self.work_days = max(self.work_days, max_day_used)
        
        # Initialize empty lists for any new days that were added
        if self.work_days > old_work_days:
            for day in range(old_work_days + 1, self.work_days + 1):
                if day not in self.appointments_by_day_and_timeslot:
                    self.appointments_by_day_and_timeslot[day] = {}
                for timeslot in range(1, self.timeslots_per_work_day + 1):
                    if timeslot not in self.appointments_by_day_and_timeslot[day]:
                        self.appointments_by_day_and_timeslot[day][timeslot] = []

def generate_schedule_using_double_flow(parsed_data: Dict) -> Schedule:
    """
    Generate a schedule using two-step approach:
    1. Assign judges to cases
    2. Assign rooms to judge-case pairs
    3. Construct conflict graph
    4. Color conflict graph for time slots
    
    Args:
        parsed_data: Dictionary containing parsed input data
        
    Returns:
        A Schedule object with the generated appointments
    """
    # Extracting input parameters
    work_days = parsed_data["work_days"]
    minutes_per_work_day = parsed_data["min_per_work_day"]
    granularity = parsed_data["granularity"]
    
    cases = parsed_data["cases"]
    judges = parsed_data["judges"]
    rooms = parsed_data["rooms"]
    
    meetings = []
    
    for case in cases:
        meetings.extend(case.meetings)
        
    # Flow 1: Assign judges to cases based on skills
    judge_meeting_graph = DirectedGraph() 
    judge_meeting_graph.initialize_meeting_to_judge_graph(meetings, judges)
    meeting_judge_pairs = assign_cases_to_judges(judge_meeting_graph)
    #judge_meeting_graph.visualize()
    
    #rooms = ensure_jm_pair_room_compatibility(meeting_judge_pairs, rooms)
    # Flow 2: Assign rooms to case-judge pairs
    jm_room_graph = DirectedGraph()
    jm_room_graph.initialize_case_judge_pair_to_room_graph(meeting_judge_pairs, rooms)
    #jm_room_graph.visualize()
    assigned_meetings = assign_meeting_judge_pairs_to_rooms(jm_room_graph)
    
    # Construct conflict graph
    conflict_graph = construct_conflict_graph(assigned_meetings, granularity)
    # conflict_graph.visualize()
    
    # Perform graph coloring
    DSatur(conflict_graph)
    
    # Generate schedule
    schedule = Schedule(work_days, minutes_per_work_day, granularity, judges, rooms, meetings, cases)
    schedule.generate_schedule_from_colored_graph(conflict_graph)
    
    return schedule
