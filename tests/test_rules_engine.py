import unittest
from src.model import Judge, Case, Attribute, Appointment, Room
from src.schedule import Schedule
from src.parser import parse_input
from src.calendar_visualizer import calendar_visualizer
from src.rules_engine import calculate_score

class TestRulesEngine(unittest.TestCase):
    
    def test_rules_on_quality_test(self):
        work_days = 1
        minutes_in_a_work_day = 390
        granularity = 5
        schedule = Schedule(work_days, minutes_in_a_work_day, granularity)
        
        parsed_data = parse_input("quality_test.json")
        cases = parsed_data["cases"]
        judges = parsed_data["judges"]
        rooms = parsed_data["rooms"]
        
        # Define case assignments (which judge and room handles which cases)
        assignments = [
            # (judge_index, room_index, case_indices)
            (0, 0, range(0, 6)),    # Judge 0, Room 0, Cases 0-5
            (1, 1, range(6, 13)),   # Judge 1, Room 1, Cases 6-12
            (2, 2, range(13, 20))   # Judge 2, Room 2, Cases 13-19
        ]
        
        # Create appointments using a loop
        for judge_idx, room_idx, case_indices in assignments:
            judge = judges[judge_idx]
            room = rooms[room_idx]
            day = 0  # All appointments are on day 0
            current_time = 0  # Start at beginning of day
            
            for case_idx in case_indices:
                case = cases[case_idx]
                slots_needed = case.case_duration // granularity
                
                # Create individual appointments for each time slot this case needs
                for slot in range(slots_needed):
                    appointment = Appointment(
                        case,
                        judge,
                        room,
                        day,
                        current_time + slot,
                        1  # Each appointment is 1 time slot long
                    )
                    schedule.appointments.append(appointment)
                
                # Update current_time for next case (add 1 slot break between cases)
                current_time += slots_needed
                     
        score = calculate_score(schedule)
        self.assertEqual(score, 0)