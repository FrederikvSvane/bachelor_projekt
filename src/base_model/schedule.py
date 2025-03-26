from collections import defaultdict
from typing import Dict

from src.util.data_generator import ensure_jm_pair_room_compatibility
from src.base_model.appointment import Appointment
from src.graph_construction.graph import UndirectedGraph, DirectedGraph, MeetingJudgeRoomNode, construct_conflict_graph

from src.graph_construction.matching import (
    assign_cases_to_judges, assign_meeting_judge_pairs_to_rooms, 
)
from src.graph_construction.coloring import DSatur


class Schedule:
    """Class that manages the court schedule."""
    
    def __init__(self, work_days: int, minutes_in_a_work_day: int, granularity: int):
        """
        Initialize a schedule with basic parameters.
        
        Args:
            work_days: Number of working days
            minutes_in_a_work_day: Minutes in a working day
            granularity: Time slot granularity in minutes
        """
        self.appointments = []
        self.work_days = work_days # 1-indexed
        self.minutes_in_a_work_day = minutes_in_a_work_day
        self.granularity = granularity
        self.timeslots_per_work_day = minutes_in_a_work_day // granularity
        
        
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
            
            # Create an appointment
            appointment = Appointment(
                node.get_meeting(),
                node.get_judge(),
                node.get_room(),
                day,
                timeslot_in_day,
                )
            self.appointments.append(appointment)
            
    def get_all_judges(self) -> list:
        """
        Returns a list of all unique judges in the schedule
        """
        judges = []
        judge_ids = set()  # Track IDs to avoid duplicates
        
        for app in self.appointments:
            if app.judge.judge_id not in judge_ids:
                judge_ids.add(app.judge.judge_id)
                judges.append(app.judge)
        
        return judges
    
    def get_all_rooms(self) -> list:
        """
        Returns a list of all unique rooms in the schedule
        """
        rooms = []
        room_ids = set()
        
        for app in self.appointments:
            if app.room.room_id not in room_ids:
                room_ids.add(app.room.room_id)
                rooms.append(app.room)
        return rooms
    
    def get_all_meetings(self) -> list:
        """
        MAYBE DONT WORK?? Returns a list of all unique cases in the schedule
        """
        meetings = []
        meeting_ids = set()
        
        for app in self.appointments:
            if app.meeting.meeting_id not in meeting_ids:
                meeting_ids.add(app.meeting.meeting_id)
                meetings.append(app.meeting)
        return meetings
    
    def get_all_cases(self) -> list:
        cases = []
        case_ids = set()
        for app in self.appointments:
            if app.meeting.case.case_id not in case_ids:
                case_ids.add(app.meeting.case.case_id)
                cases.append(app.meeting.case)
        return cases

    
    def get_time_from_timeslot(self, timeslot: int) -> str:
        """
        Convert a timeslot index into a time string.
        
        Args:
            timeslot: The timeslot index
            
        Returns:
            A string representation of the time (e.g., "09:30")
        """
        day_timeslot = timeslot % self.timeslots_per_work_day
        minutes = day_timeslot * self.granularity
        hours = minutes // 60
        minutes = minutes % 60
        
        return f"{hours:02d}:{minutes:02d}"
    
    
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
        
        for app in self.appointments:
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
    # judge_case_graph.visualize()
    
    rooms = ensure_jm_pair_room_compatibility(meeting_judge_pairs, rooms)
    # Flow 2: Assign rooms to case-judge pairs
    jm_room_graph = DirectedGraph()
    jm_room_graph.initialize_case_judge_pair_to_room_graph(meeting_judge_pairs, rooms)
    jm_room_graph.visualize()
    assigned_meetings = assign_meeting_judge_pairs_to_rooms(jm_room_graph)
    
    # Construct conflict graph
    conflict_graph = construct_conflict_graph(assigned_meetings, granularity)
    # conflict_graph.visualize()
    
    # Perform graph coloring
    DSatur(conflict_graph)
    
    # Generate schedule
    schedule = Schedule(work_days, minutes_per_work_day, granularity)
    schedule.generate_schedule_from_colored_graph(conflict_graph)
    
    
    return schedule