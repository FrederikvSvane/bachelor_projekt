from collections import defaultdict
from typing import Dict

from src.model import Case, Judge, Room, Attribute, Appointment
from src.graph import UndirectedGraph, DirectedGraph, CaseJudgeRoomNode, CaseJudgeNode, construct_conflict_graph

from src.matching import (
    assign_cases_to_judges, assign_case_judge_pairs_to_rooms, 
)
from src.coloring import DSatur
from src.graph import UndirectedGraph, DirectedGraph, CaseJudgeRoomNode
from src.model import Appointment


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
        self.work_days = work_days
        self.minutes_in_a_work_day = minutes_in_a_work_day
        self.granularity = granularity
        self.timeslots_per_work_day = minutes_in_a_work_day // granularity - 1
    
    def generate_schedule_from_colored_graph(self, graph: UndirectedGraph) -> None:
        """
        Generate appointments using the node "color" as timeslot.
        
        Args:
            graph: The colored undirected graph
        """
        for i in range(graph.get_num_nodes()):
            # Get the CaseJudgeRoomNode from the graph
            node = graph.get_node(i)
            if not isinstance(node, CaseJudgeRoomNode):
                continue
                
            # Determine the day based on timeslot (color) and timeslots per day
            day = node.get_color() // self.timeslots_per_work_day
            
            # Create an appointment
            appointment = Appointment(
                node.get_case(),
                node.get_judge(),
                node.get_room(),
                day,
                node.get_color(),
                node.get_case().case_duration
            )
            self.appointments.append(appointment)
    
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
    
    def visualize(self) -> None:
        """Visualize the schedule in a table format."""
        print("\nSchedule Visualization")
        print("=====================\n")
        print(f"Work days: {self.work_days}")
        print(f"Minutes per work day: {self.minutes_in_a_work_day}")
        print(f"Time slot granularity: {self.granularity} minutes")
        print(f"Time slots per day: {self.timeslots_per_work_day}")
        print(f"Total appointments: {len(self.appointments)}\n")
        
        # Map appointments by day
        appointments_by_day = defaultdict(list)
        for app in self.appointments:
            appointments_by_day[app.day].append(app)
        
        # Print daily schedule
        for day in range(self.work_days):
            print(f"Day {day + 1}:")
            print("-" * 70)
            print(f"{'Time':10} | {'Timeslot':10} | {'Case':10} | "
                  f"{'Judge':10} | {'Room':10} | {'Duration':10}")
            print("-" * 70)
            
            if day in appointments_by_day:
                # Sort appointments by timeslot
                day_appointments = sorted(
                    appointments_by_day[day],
                    key=lambda a: a.timeslot_start
                )
                
                # Print each appointment
                for app in day_appointments:
                    print(f"{self.get_time_from_timeslot(app.timeslot_start):10} | "
                          f"{app.timeslot_start:10} | "
                          f"{app.case.case_id:10} | "
                          f"{app.judge.judge_id:10} | "
                          f"{app.room.room_id:10} | "
                          f"{app.timeslots_duration:10} min")
            else:
                print("No appointments scheduled")
            
            print("-" * 70 + "\n")
    
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
                "timeslot_start": app.timeslot_start,
                "time": self.get_time_from_timeslot(app.timeslot_start),
                "timeslots_duration": app.timeslots_duration,
                "case": {
                    "id": app.case.case_id,
                    "duration": app.case.case_duration,
                    #"type": str(app.case.case_sagstype),
                    "virtual": app.case.case_virtual
                },
                "judge": {
                    "id": app.judge.judge_id,
                    "skills": [str(skill) for skill in app.judge.judge_skills],
                    "virtual": app.judge.judge_virtual
                },
                "room": {
                    "id": app.room.room_id,
                    "virtual": app.room.room_virtual
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
    
    # Flow 1: Assign judges to cases based on skills
    judge_case_graph = DirectedGraph() 
    judge_case_graph.initialize_case_to_judge_graph(cases, judges)
    judge_case_graph.visualize()
    case_judge_pairs = assign_cases_to_judges(judge_case_graph)
    
    # Flow 2: Assign rooms to case-judge pairs
    jc_room_graph = DirectedGraph()
    jc_room_graph.initialize_case_judge_pair_to_room_graph(case_judge_pairs, rooms)
    jc_room_graph.visualize()
    assigned_cases = assign_case_judge_pairs_to_rooms(jc_room_graph)
    
    # Construct conflict graph
    conflict_graph = construct_conflict_graph(assigned_cases)
    
    # Perform graph coloring
    DSatur(conflict_graph)
    
    # Generate schedule
    schedule = Schedule(work_days, minutes_per_work_day, granularity)
    schedule.generate_schedule_from_colored_graph(conflict_graph)
    
    return schedule