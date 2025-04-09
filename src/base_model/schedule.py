from typing import Dict

from src.util.data_generator import ensure_jm_pair_room_compatibility
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.meeting import Meeting
from src.base_model.appointment import Appointment
from src.graph_construction.graph import UndirectedGraph, DirectedGraph, MeetingJudgeRoomNode, construct_conflict_graph

from src.graph_construction.matching import (
    assign_cases_to_judges, assign_meeting_judge_pairs_to_rooms, 
)
from src.graph_construction.coloring import DSatur


class Schedule:
    """Class that manages the court schedule."""
    
    def __init__(self, work_days: int, minutes_in_a_work_day: int, granularity: int, judges: list = None, rooms: list = None):
        """
        Initialize a schedule with basic parameters.
        
        Args:
            work_days: Number of working days
            minutes_in_a_work_day: Minutes in a working day
            granularity: Time slot granularity in minutes
        """
        self.appointments_by_day = {}
        self.work_days = work_days # 1-indexed
        self.minutes_in_a_work_day = minutes_in_a_work_day
        self.granularity = granularity
        self.timeslots_per_work_day = minutes_in_a_work_day // granularity
        self.all_judges = judges
        self.all_rooms = rooms

        for day in range(1, self.work_days + 1):
            self.appointments_by_day[day] = {}
            for timeslot in range(1, self.timeslots_per_work_day + 1):
                self.appointments_by_day[day][timeslot] = []
    
    def __eq__(self, other):
        """Compare two Schedule objects for equality."""
        if not isinstance(other, Schedule):
            return False
            
        if (self.work_days != other.work_days or
                self.minutes_in_a_work_day != other.minutes_in_a_work_day or
                self.granularity != other.granularity or
                self.timeslots_per_work_day != other.timeslots_per_work_day):
            return False
            
        self_days = set(self.appointments_by_day.keys())
        other_days = set(other.appointments_by_day.keys())
        if self_days != other_days:
            return False
            
        for day in self_days:
            self_timeslots = set(self.appointments_by_day[day].keys())
            other_timeslots = set(other.appointments_by_day[day].keys())
            if self_timeslots != other_timeslots:
                return False
                
            for timeslot in self_timeslots:
                self_appointments = set(self.appointments_by_day[day][timeslot])
                other_appointments = set(other.appointments_by_day[day][timeslot])
                
                for app in self.appointments_by_day[day][timeslot]:
                    if app not in other.appointments_by_day[day][timeslot]:
                        return False
                        
                if len(self_appointments) != len(other_appointments):
                    return False
        
        if (self.all_judges is None) != (other.all_judges is None):
            return False
            
        if self.all_judges is not None:
            if len(self.all_judges) != len(other.all_judges):
                return False
                
            self_judges_map = {j.judge_id: j for j in self.all_judges}
            other_judges_map = {j.judge_id: j for j in other.all_judges}
            
            if set(self_judges_map.keys()) != set(other_judges_map.keys()):
                return False
                
            for judge_id, judge in self_judges_map.items():
                if judge != other_judges_map[judge_id]:
                    return False
        
        if (self.all_rooms is None) != (other.all_rooms is None):
            return False
            
        if self.all_rooms is not None:
            if len(self.all_rooms) != len(other.all_rooms):
                return False
                
            self_rooms_map = {r.room_id: r for r in self.all_rooms}
            other_rooms_map = {r.room_id: r for r in other.all_rooms}
            
            if set(self_rooms_map.keys()) != set(other_rooms_map.keys()):
                return False
                
            for room_id, room in self_rooms_map.items():
                if room != other_rooms_map[room_id]:
                    return False
        
        return True
            
    def iter_appointments(self):
        """
        Iterate through all appointments in the schedule
        Use like:
        for app in schedule.iter_appointments():
        """
        for day in range(1, self.work_days + 1):
            if day in self.appointments_by_day:
                for timeslot in range(1, self.timeslots_per_work_day + 1):
                    if timeslot in self.appointments_by_day[day]:
                        for app in self.appointments_by_day[day][timeslot]:
                            yield app

    def get_all_appointments(self) -> list[Appointment]:
        """Return flat list of all appointments"""
        appointments = []
        for day in range(1, self.work_days + 1):
            if day in self.appointments_by_day:
                for timeslot in range(1, self.timeslots_per_work_day + 1):
                    if timeslot in self.appointments_by_day[day]:
                        appointments.extend(self.appointments_by_day[day][timeslot])
        return appointments
            
    def get_all_judges(self) -> list:
        return self.all_judges

    def get_all_rooms(self) -> list:
        return self.all_rooms

    def get_all_meetings(self) -> list:
        meetings = []
        meeting_ids = set()
        
        for app in self.iter_appointments():
            if app.meeting.meeting_id not in meeting_ids:
                meeting_ids.add(app.meeting.meeting_id)
                meetings.append(app.meeting)
        return meetings

    def get_all_cases(self) -> list:
        cases = []
        case_ids = set()
        for app in self.iter_appointments():
            if app.meeting.case.case_id not in case_ids:
                case_ids.add(app.meeting.case.case_id)
                cases.append(app.meeting.case)
        return cases

    
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
        from src.local_search.move_generator import identify_appointment_chains
        
        chain_dict = identify_appointment_chains(self)
        
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
                        if app.day in self.appointments_by_day and app.timeslot_in_day in self.appointments_by_day[app.day]:
                            if app in self.appointments_by_day[app.day][app.timeslot_in_day]:
                                self.appointments_by_day[app.day][app.timeslot_in_day].remove(app)
                    
                    for i, app in enumerate(appointments):
                        new_timeslot = last_valid_slot + i
                        app.day = first_day
                        app.timeslot_in_day = new_timeslot
                        
                        if app.day not in self.appointments_by_day:
                            self.appointments_by_day[app.day] = {}
                        if app.timeslot_in_day not in self.appointments_by_day[app.day]:
                            self.appointments_by_day[app.day][app.timeslot_in_day] = []
                        
                        self.appointments_by_day[app.day][app.timeslot_in_day].append(app)
    
    def trim_schedule_length_if_possible(self) -> None:
        """
        Checks if the last day of the schedule is empty and removes it if so.
        Continues until a non-empty day is found or only one day remains.
        """
        while self.work_days > 1:
            last_day = self.work_days
            is_empty = True

            if last_day in self.appointments_by_day:
                for _timeslot, appointments in self.appointments_by_day[last_day].items():
                    if appointments:
                        is_empty = False
                        break 

            if is_empty:
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
        for i in range(graph.get_num_nodes()):
            # Get the CaseJudgeRoomNode from the graph
            node = graph.get_node(i)
            if not isinstance(node, MeetingJudgeRoomNode):
                continue
                
            # Determine the day based on timeslot (color) and timeslots per day
            day = node.get_color() // self.timeslots_per_work_day + 1
            timeslot_in_day = node.get_color() % self.timeslots_per_work_day + 1
            
            if day > self.work_days:
                self.appointments_by_day[day] = {}
                self.appointments_by_day[day][timeslot_in_day] = []
            
            # Create an appointment
            appointment = Appointment(
                node.get_meeting(),
                node.get_judge(),
                node.get_room(),
                day,
                timeslot_in_day,
                )
            self.appointments_by_day[day][timeslot_in_day].append(appointment)

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
    
    rooms = ensure_jm_pair_room_compatibility(meeting_judge_pairs, rooms)
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
    schedule = Schedule(work_days, minutes_per_work_day, granularity, judges, rooms)
    schedule.generate_schedule_from_colored_graph(conflict_graph)
    
    return schedule
