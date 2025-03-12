from collections import defaultdict
from typing import Dict

from src.data_generator import ensure_jc_pair_room_compatibility
from src.model import Case, Judge, Room, Attribute, Appointment
from src.graph import UndirectedGraph, DirectedGraph, CaseJudgeRoomNode, CaseJudgeNode, construct_conflict_graph

from src.matching import (
    assign_cases_to_judges, assign_case_judge_pairs_to_rooms, 
)
from src.coloring import DSatur
from src.graph import UndirectedGraph, DirectedGraph, CaseJudgeRoomNode
from src.model import Appointment
from src.schedule import Schedule



class calendar_visualizer:
    def __init__(self, judges: list[Judge], rooms: list[Room], cases: list[Case], schedule: Schedule):
        self.appointments = schedule.appointments
        self.judges = judges
        self.rooms = rooms
        self.cases = cases
        self.work_days = schedule.work_days
        self.granularity = schedule.granularity
        self.min_per_work_day = schedule.minutes_in_a_work_day
        self.timeslot_per_day = schedule.timeslots_per_work_day
    
    def generate_calendar(self):
        """
        Generate a calendar for the schedule with all judges displayed
        and appointments shown as Case/Room with continuation markers.
        """
        # Get all judges, sorted by ID
        all_judge_ids = sorted([j.judge_id for j in self.judges])
        
        # Group appointments by day
        appointments_by_day = defaultdict(list)
        for app in self.appointments:
            appointments_by_day[app.day].append(app)
        
        # For each day, create a calendar view
        for day in range(self.work_days):
            print(f"\nJudges in schedule: {all_judge_ids}")
            print(f"Day {day + 1}:")
            
            # Calculate table width based on number of judges
            col_width = 10
            total_width = 10 + (col_width + 3) * len(all_judge_ids)
            
            # Print header separator
            print("-" * total_width)
            
            # Print header with judge IDs
            print(f"{'Time':<10} | ", end="")
            for judge_id in all_judge_ids:
                print(f"{'Judge ' + str(judge_id):^{col_width}} | ", end="")
            print()
            
            # Print separator
            print("-" * total_width)
            
            # Create a grid to represent the calendar
            calendar_grid = {}
            
            if day in appointments_by_day:
                # Group appointments by case-judge-room to identify continuous blocks
                meeting_blocks = defaultdict(list)
                for app in appointments_by_day[day]:
                    key = (app.case.case_id, app.judge.judge_id, app.room.room_id)
                    meeting_blocks[key].append(app)
                
                # Process each meeting block
                for (case_id, judge_id, room_id), apps in meeting_blocks.items():
                    # Sort by timeslot
                    apps.sort(key=lambda a: a.timeslot_start)
                    
                    # Find all timeslots for this meeting
                    all_timeslots = set()
                    for app in apps:
                        timeslot = app.timeslot_start % self.timeslot_per_day
                        all_timeslots.add(timeslot)
                    
                    # Find the starting timeslot (lowest)
                    start_timeslot = min(all_timeslots)
                    
                    # Mark the starting slot with the case/room identifier
                    calendar_grid[(start_timeslot, judge_id)] = f"C{case_id}/R{room_id}"
                    
                    # Mark all other slots of this meeting with continuation markers
                    for timeslot in all_timeslots:
                        if timeslot != start_timeslot:
                            calendar_grid[(timeslot, judge_id)] = "#########"
                           
            # Print each timeslot row
            for timeslot in range(self.timeslot_per_day):  # Limit to reasonable number of slots
                # Calculate time string - starting at 08:30
                base_minutes = 8 * 60 + 30  # 8 hours and 30 minutes in minutes
                total_minutes = base_minutes + (timeslot * self.granularity)
                hours = total_minutes // 60
                minutes = total_minutes % 60
                time_str = f"{hours:02d}:{minutes:02d}"
                
                print(f"{time_str:<10} | ", end="")
                
                for judge_id in all_judge_ids:
                    cell_content = calendar_grid.get((timeslot, judge_id), "")
                    print(f"{cell_content:^{col_width}} | ", end="")
                print()
            
            # Print footer separator
            print("-" * total_width)