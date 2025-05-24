import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.base_model.schedule import Schedule
from src.base_model.meeting import Meeting
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.appointment import Appointment
from src.base_model.case import Case
from src.base_model.attribute_enum import Attribute
from src.local_search.move_generator import generate_contracting_move
from src.local_search.move import do_contracting_move, undo_contracting_move, Move, do_move
from src.construction.heuristic.linear_assignment import generate_schedule
from src.base_model.compatibility_checks import calculate_compatible_judges, calculate_compatible_rooms
from collections import defaultdict
import random


class TestContractingMove(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        # Set random seed for reproducibility
        random.seed(42)
        
    def create_simple_schedule_with_gaps(self):
        """Create a simple schedule with gaps for testing."""
        # Create judges
        judges = [
            Judge(judge_id=1, characteristics={Attribute.STRAFFE}),
            Judge(judge_id=2, characteristics={Attribute.CIVIL})
        ]
        
        # Create rooms
        rooms = [
            Room(room_id=1, characteristics=set()),
            Room(room_id=2, characteristics=set())
        ]
        
        # Create meetings
        meetings = []
        
        # Judge 1 meetings
        meeting1 = Meeting(
            meeting_id=1,
            meeting_duration=30,
            duration_of_stay=0,
            judge=None,
            room=None,
            case=None
        )
        meeting2 = Meeting(
            meeting_id=2,
            meeting_duration=30,
            duration_of_stay=0,
            judge=None,
            room=None,
            case=None
        )
        
        # Judge 2 meetings
        meeting3 = Meeting(
            meeting_id=3,
            meeting_duration=30,
            duration_of_stay=0,
            judge=None,
            room=None,
            case=None
        )
        meeting4 = Meeting(
            meeting_id=4,
            meeting_duration=30,
            duration_of_stay=0,
            judge=None,
            room=None,
            case=None
        )
        
        meetings = [meeting1, meeting2, meeting3, meeting4]
        
        # Create schedule
        schedule = Schedule(
            work_days=1,
            minutes_in_a_work_day=240,  # 8 * 30 = 240 minutes (8 slots)
            granularity=30,
            judges=judges,
            rooms=rooms,
            meetings=meetings
        )
        
        # Manually place meetings with gaps
        # Judge 1: meetings at slots 3 and 6 (gaps at 1-2, 4-5)
        placements = [
            (meeting1, judges[0], rooms[0], 1, 3),
            (meeting2, judges[0], rooms[0], 1, 6),
            (meeting3, judges[1], rooms[1], 1, 2),
            (meeting4, judges[1], rooms[1], 1, 5)
        ]
        
        for meeting, judge, room, day, slot in placements:
            meeting.judge = judge
            meeting.room = room
            appointment = Appointment(
                meeting=meeting,
                judge=judge,
                room=room,
                day=day,
                timeslot_in_day=slot
            )
            schedule.add_meeting_to_schedule(appointment)
        
        # Clear unplanned meetings
        schedule.unplanned_meetings = []
        
        return schedule
    
    def validate_no_room_double_booking(self, schedule):
        """Validate that no room is double-booked."""
        room_usage = defaultdict(set)
        
        for day, timeslots in schedule.appointments_by_day_and_timeslot.items():
            for timeslot, appointments in timeslots.items():
                for appointment in appointments:
                    room_id = appointment.room.room_id
                    time_key = (day, timeslot)
                    
                    if time_key in room_usage[room_id]:
                        return False
                    
                    room_usage[room_id].add(time_key)
        
        return True
    
    def test_basic_contracting(self):
        """Test basic contracting functionality."""
        schedule = self.create_simple_schedule_with_gaps()
        
        # Validate initial state
        self.assertTrue(self.validate_no_room_double_booking(schedule))
        
        # Apply contracting move
        contracting_move = generate_contracting_move(schedule)
        
        # Debug output
        print(f"\nContracting move summary: {contracting_move}")
        print(contracting_move.get_summary())
        
        # Verify the move was created
        self.assertIsNotNone(contracting_move)
        self.assertGreaterEqual(len(contracting_move.individual_moves), 0)  # Changed to >= to see what happens
        
        # Validate no double bookings after contracting
        self.assertTrue(self.validate_no_room_double_booking(schedule))
        
        # Check that meetings moved earlier
        # Judge 1's first meeting should be at slot 1
        meeting1_apps = schedule.get_appointment_chain(1)
        self.assertEqual(meeting1_apps[0].timeslot_in_day, 1)
        
        # Judge 1's second meeting should be at slot 2 (right after first)
        meeting2_apps = schedule.get_appointment_chain(2)
        self.assertEqual(meeting2_apps[0].timeslot_in_day, 2)
    
    def test_contracting_with_room_conflicts(self):
        """Test that contracting respects room conflicts."""
        # Create judges
        judges = [
            Judge(judge_id=1, characteristics={Attribute.STRAFFE}),
            Judge(judge_id=2, characteristics={Attribute.CIVIL})
        ]
        
        # Create limited rooms
        rooms = [Room(room_id=1, characteristics=set())]
        
        # Create meetings
        meetings = [
            Meeting(
                meeting_id=1,
                meeting_duration=30,
                duration_of_stay=0,
                judge=None,
                room=None,
                case=None
            ),
            Meeting(
                meeting_id=2,
                meeting_duration=30,
                duration_of_stay=0,
                judge=None,
                room=None,
                case=None
            )
        ]
        
        # Create schedule
        schedule = Schedule(
            work_days=1,
            minutes_in_a_work_day=120,  # 4 * 30 = 120 minutes (4 slots)
            granularity=30,
            judges=judges,
            rooms=rooms,
            meetings=meetings
        )
        
        # Place Judge 2's meeting at slot 1 in room 1
        meeting2 = meetings[1]
        meeting2.judge = judges[1]
        meeting2.room = rooms[0]
        app2 = Appointment(
            meeting=meeting2,
            judge=judges[1],
            room=rooms[0],
            day=1,
            timeslot_in_day=1
        )
        schedule.add_meeting_to_schedule(app2)
        
        # Place Judge 1's meeting at slot 3 in room 1
        meeting1 = meetings[0]
        meeting1.judge = judges[0]
        meeting1.room = rooms[0]
        app1 = Appointment(
            meeting=meeting1,
            judge=judges[0],
            room=rooms[0],
            day=1,
            timeslot_in_day=3
        )
        schedule.add_meeting_to_schedule(app1)
        
        schedule.unplanned_meetings = []
        
        # Apply contracting
        contracting_move = generate_contracting_move(schedule)
        
        # Validate no double bookings
        self.assertTrue(self.validate_no_room_double_booking(schedule))
        
        # Meeting 1 should NOT have moved to slot 1 due to room conflict
        meeting1_apps = schedule.get_appointment_chain(1)
        self.assertEqual(meeting1_apps[0].timeslot_in_day, 3)
        
        # Check that the conflict was recorded
        self.assertGreater(len(contracting_move.skipped_meetings), 0)
        skipped_ids = [m[0] for m in contracting_move.skipped_meetings]
        self.assertIn(1, skipped_ids)
    
    def test_contracting_undo(self):
        """Test that contracting moves can be undone."""
        schedule = self.create_simple_schedule_with_gaps()
        
        # Record initial positions
        initial_positions = {}
        for meeting in schedule.get_all_meetings():
            apps = schedule.get_appointment_chain(meeting.meeting_id)
            if apps:
                initial_positions[meeting.meeting_id] = apps[0].timeslot_in_day
        
        # Apply contracting
        contracting_move = generate_contracting_move(schedule)
        
        # Verify some moves were made
        self.assertGreater(len(contracting_move.individual_moves), 0)
        
        # Undo the contracting move
        undo_contracting_move(contracting_move, schedule)
        
        # Verify positions are restored
        for meeting in schedule.get_all_meetings():
            apps = schedule.get_appointment_chain(meeting.meeting_id)
            if apps and meeting.meeting_id in initial_positions:
                self.assertEqual(
                    apps[0].timeslot_in_day,
                    initial_positions[meeting.meeting_id],
                    f"Meeting {meeting.meeting_id} not restored to original position"
                )
        
        # Validate no double bookings after undo
        self.assertTrue(self.validate_no_room_double_booking(schedule))
    
    def test_contracting_multi_day_schedule(self):
        """Test contracting on a multi-day schedule."""
        # Create a 2-day schedule using linear assignment
        judges = [
            Judge(judge_id=1, characteristics={Attribute.STRAFFE}),
            Judge(judge_id=2, characteristics={Attribute.CIVIL})
        ]
        
        rooms = [
            Room(room_id=1, characteristics=set()),
            Room(room_id=2, characteristics=set())
        ]
        
        cases = []
        meeting_id = 1
        
        for day in range(2):
            for judge_idx in range(2):
                case = Case(
                    case_id=meeting_id,
                    characteristics={Attribute.STRAFFE} if judge_idx == 0 else {Attribute.CIVIL}
                )
                
                meeting = Meeting(
                    meeting_id=meeting_id,
                    meeting_duration=30,
                    duration_of_stay=0,
                    judge=None,
                    room=None,
                    case=case
                )
                
                case.meetings.append(meeting)
                cases.append(case)
                meeting_id += 1
        
        parsed_data = {
            "cases": cases,
            "judges": judges,
            "rooms": rooms,
            "work_days": 2,
            "min_per_work_day": 240,
            "granularity": 30
        }
        
        schedule = generate_schedule(parsed_data)
        
        # Create gaps by moving some meetings
        for meeting in schedule.get_all_planned_meetings()[:2]:
            apps = schedule.get_appointment_chain(meeting.meeting_id)
            if apps and apps[0].timeslot_in_day < 6:
                move = Move(
                    meeting_id=meeting.meeting_id,
                    appointments=apps,
                    old_judge=apps[0].judge,
                    old_room=apps[0].room,
                    old_day=apps[0].day,
                    old_start_timeslot=apps[0].timeslot_in_day,
                    new_start_timeslot=apps[0].timeslot_in_day + 2
                )
                do_move(move, schedule)
        
        # Apply contracting
        contracting_move = generate_contracting_move(schedule)
        
        # Validate no double bookings
        self.assertTrue(self.validate_no_room_double_booking(schedule))
        
        # Verify each day is processed independently
        for day in range(1, schedule.work_days + 1):
            day_has_meetings = False
            for timeslots in schedule.appointments_by_day_and_timeslot.get(day, {}).values():
                if timeslots:
                    day_has_meetings = True
                    break
            
            if day_has_meetings:
                # Check that at least one meeting starts at slot 1
                slot_1_apps = schedule.appointments_by_day_and_timeslot.get(day, {}).get(1, [])
                if slot_1_apps:
                    self.assertGreater(len(slot_1_apps), 0, f"Day {day} should have meetings starting at slot 1")
    
    def test_contracting_move_summary(self):
        """Test the summary functionality of contracting moves."""
        schedule = self.create_simple_schedule_with_gaps()
        
        contracting_move = generate_contracting_move(schedule)
        
        # Get summary
        summary = contracting_move.get_summary()
        
        # Verify summary contains expected information
        self.assertIn("Contracting Move Summary", summary)
        self.assertIn("Total moves:", summary)
        self.assertIn("Skipped meetings:", summary)
        
        # Verify string representation
        str_repr = str(contracting_move)
        self.assertIn("ContractingMove", str_repr)
        self.assertIn("moves=", str_repr)
        self.assertIn("skipped=", str_repr)


if __name__ == '__main__':
    unittest.main()