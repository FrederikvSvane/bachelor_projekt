import unittest
import sys
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.construction.ilp.ilp_solver import generate_schedule_using_ilp
from src.util.data_generator import generate_test_data_parsed
from src.base_model.compatibility_checks import initialize_compatibility_matricies
from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.meeting import Meeting
from src.base_model.attribute_enum import Attribute


class TestILPSolver(unittest.TestCase):
    
    def test_basic_ilp_scheduling(self):
        """Test ILP solver with a small random dataset"""
        # Generate small test data
        n_cases = 5
        n_work_days = 1
        granularity = 30  # 30 minute slots
        min_per_work_day = 240  # 4 hours
        
        parsed_data = generate_test_data_parsed(
            n_cases=n_cases, 
            work_days=n_work_days, 
            granularity=granularity, 
            min_per_work_day=min_per_work_day
        )
        initialize_compatibility_matricies(parsed_data)
        
        # Generate schedule using ILP
        schedule = generate_schedule_using_ilp(parsed_data)
        
        # Verify basic properties
        self.assertIsNotNone(schedule, "Schedule should not be None")
        self.assertEqual(schedule.work_days, n_work_days)
        self.assertEqual(schedule.minutes_in_a_work_day, min_per_work_day)
        self.assertEqual(schedule.granularity, granularity)
        
        # Check if any appointments were scheduled
        # Note: Depending on compatibility, not all cases may be schedulable
        appointment_count = sum(1 for _ in schedule.iter_appointments())
        print(f"Scheduled {appointment_count} appointments for {n_cases} cases")
        
    def test_consecutive_slots_enforcement(self):
        """Test that ILP solver schedules meetings in consecutive time slots"""
        # Create a simple test case with controlled data
        case1 = Case(
            case_id="C1",
            judge_requirements=set(),
            room_requirements=set(),
            characteristics={Attribute.STRAFFE}
        )
        
        # Create a meeting for the case
        meeting1 = Meeting(
            meeting_id=1,
            meeting_duration=90,  # 3 slots of 30 minutes
            duration_of_stay=0,
            judge=None,
            room=None,
            case=case1
        )
        
        case1.meetings = [meeting1]
        
        parsed_data = {
            "work_days": 1,
            "min_per_work_day": 300,  # 5 hours
            "granularity": 30,  # 30 minute slots
            "cases": [case1],
            "meetings": [meeting1],
            "judges": [
                Judge(
                    judge_id="J1",
                    characteristics={Attribute.STRAFFE},
                    case_requirements=set(),
                    room_requirements=set()
                )
            ],
            "rooms": [
                Room(
                    room_id="R1",
                    characteristics=set(),
                    case_requirements=set(),
                    judge_requirements=set()
                )
            ]
        }
        
        initialize_compatibility_matricies(parsed_data)
        schedule = generate_schedule_using_ilp(parsed_data)
        
        # Get appointments for the case
        case_appointments = [a for a in schedule.iter_appointments() if a.meeting.case.case_id == "C1"]
        
        if len(case_appointments) > 0:
            self.assertEqual(len(case_appointments), 3, 
                           "Meeting with 90 minute duration should have 3 appointments of 30 minutes each")
            
            # Verify appointments are consecutive
            case_appointments.sort(key=lambda a: (a.day, a.timeslot_in_day))
            for i in range(1, len(case_appointments)):
                prev = case_appointments[i-1]
                curr = case_appointments[i]
                
                if prev.day == curr.day:
                    self.assertEqual(curr.timeslot_in_day, prev.timeslot_in_day + 1,
                                   "Appointments should be in consecutive time slots")
                else:
                    self.assertEqual(curr.day, prev.day + 1, "Days should be consecutive")
                    self.assertEqual(curr.timeslot_in_day, 0, "New day should start at slot 0")
                    
    def test_compatibility_respected(self):
        """Test that ILP solver respects compatibility constraints"""
        # Create cases
        case1 = Case(
            case_id="C1",
            judge_requirements={Attribute.CIVIL},  # Requires civil judge
            room_requirements=set(),
            characteristics={Attribute.STRAFFE}
        )
        
        meeting1 = Meeting(
            meeting_id=1,
            meeting_duration=60,
            duration_of_stay=0,
            judge=None,
            room=None,
            case=case1
        )
        
        case1.meetings = [meeting1]
        
        parsed_data = {
            "work_days": 1,
            "min_per_work_day": 120,  # 2 hours
            "granularity": 60,  # 1 hour slots
            "cases": [case1],
            "meetings": [meeting1],
            "judges": [
                Judge(
                    judge_id="J1",
                    characteristics={Attribute.STRAFFE},  # Not compatible
                    case_requirements=set(),
                    room_requirements=set()
                ),
                Judge(
                    judge_id="J2",
 
                    characteristics={Attribute.CIVIL},  # Compatible
                    case_requirements=set(),
                    room_requirements=set()
                )
            ],
            "rooms": [
                Room(
                    room_id="R1",
                    characteristics=set(),
                    case_requirements=set(),
                    judge_requirements=set()
                )
            ]
        }
        
        initialize_compatibility_matricies(parsed_data)
        schedule = generate_schedule_using_ilp(parsed_data)
        
        # Check that case is assigned to the civil judge
        case_appointments = [a for a in schedule.iter_appointments() if a.meeting.case.case_id == "C1"]
        
        if len(case_appointments) > 0:
            for appointment in case_appointments:
                self.assertEqual(appointment.judge.judge_id, "J2",
                               "Case should be assigned to the civil judge")
                
    def test_no_double_booking(self):
        """Test that ILP solver prevents double booking of judges and rooms"""
        n_cases = 10
        n_work_days = 1
        granularity = 30
        min_per_work_day = 240  # 4 hours = 8 slots
        
        parsed_data = generate_test_data_parsed(
            n_cases=n_cases,
            work_days=n_work_days,
            granularity=granularity,
            min_per_work_day=min_per_work_day
        )
        initialize_compatibility_matricies(parsed_data)
        
        schedule = generate_schedule_using_ilp(parsed_data)
        
        # Check for judge double-booking
        judge_timeslots = {}
        for appointment in schedule.iter_appointments():
            key = (appointment.judge.judge_id, appointment.day, appointment.timeslot_in_day)
            self.assertNotIn(key, judge_timeslots,
                           f"Judge {appointment.judge.judge_id} is double-booked")
            judge_timeslots[key] = appointment.meeting.case.case_id
            
        # Check for room double-booking  
        room_timeslots = {}
        for appointment in schedule.iter_appointments():
            key = (appointment.room.room_id, appointment.day, appointment.timeslot_in_day)
            self.assertNotIn(key, room_timeslots,
                           f"Room {appointment.room.room_id} is double-booked")
            room_timeslots[key] = appointment.meeting.case.case_id
            
    def test_larger_problem_instance(self):
        """Test ILP solver with a larger problem instance"""
        n_cases = 20
        n_work_days = 2
        granularity = 15  # 15 minute slots
        min_per_work_day = 480  # 8 hours
        
        parsed_data = generate_test_data_parsed(
            n_cases=n_cases,
            work_days=n_work_days,
            granularity=granularity,
            min_per_work_day=min_per_work_day
        )
        initialize_compatibility_matricies(parsed_data)
        
        # This might take longer to solve
        print(f"\nTesting ILP solver with {n_cases} cases over {n_work_days} days...")
        schedule = generate_schedule_using_ilp(parsed_data)
        
        # Just verify it returns a valid schedule structure
        self.assertIsNotNone(schedule)
        self.assertEqual(schedule.work_days, n_work_days)
        
        # Count how many cases were successfully scheduled
        scheduled_cases = set()
        for appointment in schedule.iter_appointments():
            scheduled_cases.add(appointment.meeting.case.case_id)
            
        print(f"Successfully scheduled {len(scheduled_cases)} out of {n_cases} cases")
        appointment_count = sum(1 for _ in schedule.iter_appointments())
        print(f"Total appointments: {appointment_count}")
        
    def test_meeting_cannot_cross_day_boundary(self):
        """Test that meetings cannot be scheduled across day boundaries"""
        # Create a case with a long meeting that would cross day boundary if scheduled late
        case1 = Case(
            case_id="C1",
            judge_requirements=set(),
            room_requirements=set(),
            characteristics={Attribute.STRAFFE}
        )
        
        # Create a meeting that's 4 hours long (240 minutes)
        meeting1 = Meeting(
            meeting_id=1,
            meeting_duration=240,  # 4 hours
            duration_of_stay=0,
            judge=None,
            room=None,
            case=case1
        )
        
        case1.meetings = [meeting1]
        
        parsed_data = {
            "work_days": 2,
            "min_per_work_day": 390,  # 6.5 hours
            "granularity": 30,  # 30 minute slots
            "cases": [case1],
            "meetings": [meeting1],
            "judges": [
                Judge(
                    judge_id="J1",
                    characteristics={Attribute.STRAFFE},
                    case_requirements=set(),
                    room_requirements=set()
                )
            ],
            "rooms": [
                Room(
                    room_id="R1",
                    characteristics=set(),
                    case_requirements=set(),
                    judge_requirements=set()
                )
            ]
        }
        
        initialize_compatibility_matricies(parsed_data)
        schedule = generate_schedule_using_ilp(parsed_data)
        
        # Get all appointments for the meeting
        meeting_appointments = [a for a in schedule.iter_appointments() if a.meeting.meeting_id == 1]
        
        if len(meeting_appointments) > 0:
            # Sort appointments by time
            meeting_appointments.sort(key=lambda a: (a.day, a.timeslot_in_day))
            
            # Check that all appointments are on the same day
            days = set(a.day for a in meeting_appointments)
            self.assertEqual(len(days), 1, "Meeting should not span multiple days")
            
            # Check that the meeting doesn't exceed the day's timeslots
            # With 390 minutes and 30-minute granularity, we have 13 timeslots per day
            timeslots_per_day = 390 // 30  # = 13
            
            last_appointment = meeting_appointments[-1]
            
            # Verify last timeslot doesn't exceed the day
            self.assertLessEqual(last_appointment.timeslot_in_day, timeslots_per_day,
                               f"Meeting should not extend beyond timeslot {timeslots_per_day}")
            
            # Verify the meeting has the correct number of appointments
            expected_appointments = 240 // 30  # = 8 appointments
            self.assertEqual(len(meeting_appointments), expected_appointments,
                           f"Meeting should have {expected_appointments} appointments")
                           
    def test_schedule_length_minimization(self):
        """Test that ILP solver minimizes schedule length"""
        # Create multiple cases that can all fit on day 1 
        cases = []
        meetings = []
        
        for i in range(3):
            case = Case(
                case_id=f"C{i+1}",
                judge_requirements=set(),
                room_requirements=set(),
                characteristics={Attribute.STRAFFE}
            )
            
            meeting = Meeting(
                meeting_id=i+1,
                meeting_duration=30,  # 1 slot each
                duration_of_stay=0,
                judge=None,
                room=None,
                case=case
            )
            
            case.meetings = [meeting]
            cases.append(case)
            meetings.append(meeting)
        
        parsed_data = {
            "work_days": 5,  # Give it lots of days to choose from
            "min_per_work_day": 480,  # 8 hours = 16 slots of 30 min
            "granularity": 30,
            "cases": cases,
            "meetings": meetings,
            "judges": [
                Judge(
                    judge_id="J1",
                    characteristics={Attribute.STRAFFE},
                    case_requirements=set(),
                    room_requirements=set()
                )
            ],
            "rooms": [
                Room(
                    room_id="R1",
                    characteristics=set(),
                    case_requirements=set(),
                    judge_requirements=set()
                )
            ]
        }
        
        initialize_compatibility_matricies(parsed_data)
        schedule = generate_schedule_using_ilp(parsed_data)
        
        # Get all appointments
        appointments = list(schedule.iter_appointments())
        
        if len(appointments) > 0:
            # All meetings should be scheduled on day 1 to minimize schedule length
            days_used = set(a.day for a in appointments)
            self.assertEqual(len(days_used), 1, "All meetings should be scheduled on the same day to minimize schedule length")
            self.assertEqual(min(days_used), 1, "Meetings should be scheduled on day 1")
            
            # Count timeslots used
            used_timeslots_day1 = set(a.timeslot_in_day for a in appointments if a.day == 1)
            print(f"Day 1: Used {len(used_timeslots_day1)} timeslots")
            
            # With 3 meetings of 1 slot each, we should use exactly 3 timeslots
            self.assertEqual(len(used_timeslots_day1), 3, "Should use exactly 3 timeslots for 3 meetings")
            
    def test_schedule_compactness(self):
        """Test that ILP creates compact schedules"""
        # Create a scenario with multiple judges and meetings
        cases = []
        meetings = []
        
        for i in range(4):
            case = Case(
                case_id=f"C{i+1}",
                judge_requirements=set(),
                room_requirements=set(),
                characteristics={Attribute.STRAFFE}
            )
            
            meeting = Meeting(
                meeting_id=i+1,
                meeting_duration=60,  # 2 slots each
                duration_of_stay=0,
                judge=None,
                room=None,
                case=case
            )
            
            case.meetings = [meeting]
            cases.append(case)
            meetings.append(meeting)
        
        parsed_data = {
            "work_days": 3,
            "min_per_work_day": 240,  # 4 hours = 8 slots of 30 min
            "granularity": 30,
            "cases": cases,
            "meetings": meetings,
            "judges": [
                Judge(
                    judge_id="J1",
                    characteristics={Attribute.STRAFFE},
                    case_requirements=set(),
                    room_requirements=set()
                ),
                Judge(
                    judge_id="J2", 
                    characteristics={Attribute.STRAFFE},
                    case_requirements=set(),
                    room_requirements=set()
                )
            ],
            "rooms": [
                Room(
                    room_id="R1",
                    characteristics=set(),
                    case_requirements=set(),
                    judge_requirements=set()
                ),
                Room(
                    room_id="R2",
                    characteristics=set(),
                    case_requirements=set(),
                    judge_requirements=set()
                )
            ]
        }
        
        initialize_compatibility_matricies(parsed_data)
        schedule = generate_schedule_using_ilp(parsed_data)
        
        appointments = list(schedule.iter_appointments())
        
        if len(appointments) > 0:
            # Check that schedule is compact (uses minimal days)
            days_used = set(a.day for a in appointments)
            print(f"Schedule uses {len(days_used)} days: {sorted(days_used)}")
            
            # With 4 meetings of 2 slots each = 8 slots total
            # With 2 judges and 2 rooms, we can fit 2 meetings per day
            # So optimal is 2 days
            self.assertLessEqual(len(days_used), 2, "Schedule should use at most 2 days")
    
    def test_early_scheduling_preference(self):
        """Test that ILP solver prefers to schedule meetings early in the day"""
        # Create a scenario where meetings can be scheduled at different times
        cases = []
        meetings = []
        
        # Create 3 meetings of 1 hour each
        for i in range(3):
            case = Case(
                case_id=f"C{i+1}",
                judge_requirements=set(),
                room_requirements=set(),
                characteristics={Attribute.STRAFFE}
            )
            
            meeting = Meeting(
                meeting_id=i+1,
                meeting_duration=60,  # 1 hour = 2 slots of 30 min
                duration_of_stay=0,
                judge=None,
                room=None,
                case=case
            )
            
            case.meetings = [meeting]
            cases.append(case)
            meetings.append(meeting)
        
        parsed_data = {
            "work_days": 1,
            "min_per_work_day": 480,  # 8 hours = 16 slots
            "granularity": 30,
            "cases": cases,
            "meetings": meetings,
            "judges": [
                Judge(
                    judge_id="J1",
                    characteristics={Attribute.STRAFFE},
                    case_requirements=set(),
                    room_requirements=set()
                )
            ],
            "rooms": [
                Room(
                    room_id="R1",
                    characteristics=set(),
                    case_requirements=set(),
                    judge_requirements=set()
                )
            ]
        }
        
        initialize_compatibility_matricies(parsed_data)
        schedule = generate_schedule_using_ilp(parsed_data)
        
        # Get all appointments
        appointments = list(schedule.iter_appointments())
        
        if len(appointments) == 6:  # 3 meetings × 2 slots each
            # Get the start times of all meetings
            meeting_starts = {}
            for a in appointments:
                if a.meeting.meeting_id not in meeting_starts:
                    meeting_starts[a.meeting.meeting_id] = a.timeslot_in_day
                else:
                    meeting_starts[a.meeting.meeting_id] = min(meeting_starts[a.meeting.meeting_id], a.timeslot_in_day)
            
            sorted_starts = sorted(meeting_starts.values())
            print(f"Meeting start times: {sorted_starts}")
            
            # With early scheduling preference, meetings should start as early as possible
            # Ideal: timeslots 1, 3, 5 (consecutive 2-slot meetings)
            self.assertEqual(sorted_starts[0], 1, "First meeting should start at timeslot 1")
            
            # Check that meetings are scheduled consecutively (no gaps)
            expected_starts = [1, 3, 5]  # For 3 meetings of 2 slots each
            self.assertEqual(sorted_starts, expected_starts, "Meetings should be scheduled consecutively from the start")
    
    def test_performance_with_minimal_schedule_length(self):
        """Test ILP solver performance with the simplified schedule length minimization"""
        import time
        
        test_cases = [
            (5, 3, 5.0),    # 5 cases, 3 days, expect under 5 seconds
            (10, 3, 10.0),  # 10 cases, 3 days, expect under 10 seconds
            (15, 5, 30.0),  # 15 cases, 5 days, expect under 30 seconds (was 85+ seconds before)
        ]
        
        for n_cases, n_days, max_time in test_cases:
            print(f"\nTesting performance with {n_cases} cases and {n_days} days...")
            
            parsed_data = generate_test_data_parsed(
                n_cases=n_cases,
                work_days=n_days,
                granularity=30,  # 30 minute slots
                min_per_work_day=480  # 8 hours
            )
            initialize_compatibility_matricies(parsed_data)
            
            start_time = time.time()
            schedule = generate_schedule_using_ilp(parsed_data)
            total_time = time.time() - start_time
            
            print(f"ILP solver completed in {total_time:.2f} seconds")
            
            # Count results
            appointments = list(schedule.iter_appointments())
            days_used = set(a.day for a in appointments) if appointments else set()
            print(f"Scheduled {len(appointments)} appointments using {len(days_used)} days")
            
            # Assert performance is acceptable
            self.assertLess(total_time, max_time, 
                          f"ILP solver took {total_time:.2f}s, expected under {max_time}s for {n_cases} cases")


if __name__ == "__main__":
    unittest.main()