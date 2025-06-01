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
from src.local_search.rules_engine import calculate_full_score, nr31_distance_between_meetings_full
from src.local_search.rules_engine_helpers import calculate_gaps_between_appointments
from src.local_search.move_generator import generate_contracting_move
from src.local_search.move import do_move
from src.base_model.compatibility_checks import initialize_compatibility_matricies


class TestGapScoring(unittest.TestCase):
    """Test that gap scoring correctly counts gaps from start of day."""
    
    def test_gap_from_start_of_day(self):
        """Test that gaps from slot 1 to first meeting are counted."""
        print("\n=== Testing Gap Scoring from Start of Day ===")
        
        # Create minimal setup
        judge = Judge(judge_id=1, characteristics={Attribute.STRAFFE})
        room = Room(room_id=1, characteristics=set())
        
        case = Case(case_id=1, characteristics={Attribute.STRAFFE})
        meeting = Meeting(
            meeting_id=1,
            meeting_duration=30,
            duration_of_stay=0,
            judge=None,
            room=None,
            case=case
        )
        
        schedule = Schedule(
            work_days=1,
            minutes_in_a_work_day=240,
            granularity=30,
            judges=[judge],
            rooms=[room],
            meetings=[meeting],
            cases=[case]
        )
        
        # Test case 1: Meeting at slot 1 (no gap)
        meeting.judge = judge
        meeting.room = room
        app1 = Appointment(
            meeting=meeting,
            judge=judge,
            room=room,
            day=1,
            timeslot_in_day=1
        )
        schedule.add_meeting_to_schedule(app1)
        schedule.initialize_appointment_chains()
        
        # Initialize compatibility matrices
        case.meetings.append(meeting)
        parsed_data = {"cases": [case], "judges": [judge], "rooms": [room]}
        initialize_compatibility_matricies(parsed_data)
        
        gaps_slot1 = calculate_gaps_between_appointments(schedule, judge.judge_id)
        score_slot1 = nr31_distance_between_meetings_full(schedule)
        
        print(f"\nMeeting at slot 1:")
        print(f"  Gaps counted: {gaps_slot1}")
        print(f"  Rule 31 score: {score_slot1}")
        
        # Clear and test case 2: Meeting at slot 5 (gap from slot 1-4)
        schedule.appointments_by_day_and_timeslot[1].clear()
        schedule.appointment_chains.clear()
        
        app2 = Appointment(
            meeting=meeting,
            judge=judge,
            room=room,
            day=1,
            timeslot_in_day=5
        )
        schedule.add_meeting_to_schedule(app2)
        schedule.initialize_appointment_chains()
        
        gaps_slot5 = calculate_gaps_between_appointments(schedule, judge.judge_id)
        score_slot5 = nr31_distance_between_meetings_full(schedule)
        
        print(f"\nMeeting at slot 5:")
        print(f"  Gaps counted: {gaps_slot5}")
        print(f"  Rule 31 score: {score_slot5}")
        
        # Verify gap is counted
        self.assertEqual(gaps_slot1, 0, "No gap should be counted when meeting starts at slot 1")
        self.assertEqual(gaps_slot5, 1, "One gap should be counted when meeting starts at slot 5")
        self.assertGreater(score_slot5, score_slot1, "Score should be worse when there's a gap")
    
    def test_contracting_move_improves_score(self):
        """Test that contracting moves improve the score."""
        print("\n=== Testing Contracting Move Score Improvement ===")
        
        # Create schedule with gap
        judge = Judge(judge_id=1, characteristics={Attribute.STRAFFE})
        room = Room(room_id=1, characteristics=set())
        
        case = Case(case_id=1, characteristics={Attribute.STRAFFE})
        meeting = Meeting(
            meeting_id=1,
            meeting_duration=30,
            duration_of_stay=0,
            judge=None,
            room=None,
            case=case
        )
        
        schedule = Schedule(
            work_days=1,
            minutes_in_a_work_day=240,
            granularity=30,
            judges=[judge],
            rooms=[room],
            meetings=[meeting],
            cases=[case]
        )
        
        # Place meeting at slot 3
        meeting.judge = judge
        meeting.room = room
        app = Appointment(
            meeting=meeting,
            judge=judge,
            room=room,
            day=1,
            timeslot_in_day=3
        )
        schedule.add_meeting_to_schedule(app)
        schedule.initialize_appointment_chains()
        
        # Initialize compatibility matrices
        case.meetings.append(meeting)
        parsed_data = {"cases": [case], "judges": [judge], "rooms": [room]}
        initialize_compatibility_matricies(parsed_data)
        
        # Get scores before contracting
        gaps_before = calculate_gaps_between_appointments(schedule, judge.judge_id)
        full_score_before = calculate_full_score(schedule)
        rule31_before = nr31_distance_between_meetings_full(schedule)
        
        print(f"\nBefore contracting:")
        print(f"  Meeting at slot: 3")
        print(f"  Gaps: {gaps_before}")
        print(f"  Rule 31 score: {rule31_before}")
        print(f"  Full score: {full_score_before}")
        
        # Apply contracting move
        contracting_move = generate_contracting_move(schedule)
        
        # Get scores after contracting
        gaps_after = calculate_gaps_between_appointments(schedule, judge.judge_id)
        full_score_after = calculate_full_score(schedule)
        rule31_after = nr31_distance_between_meetings_full(schedule)
        
        # Get meeting's new position
        new_slot = schedule.get_appointment_chain(1)[0].timeslot_in_day
        
        print(f"\nAfter contracting:")
        print(f"  Meeting at slot: {new_slot}")
        print(f"  Gaps: {gaps_after}")
        print(f"  Rule 31 score: {rule31_after}")
        print(f"  Full score: {full_score_after}")
        print(f"  Moves made: {len(contracting_move.individual_moves)}")
        
        # Verify improvement
        self.assertEqual(new_slot, 1, "Meeting should be moved to slot 1")
        self.assertEqual(gaps_after, 0, "No gaps should remain")
        self.assertLess(rule31_after, rule31_before, "Rule 31 score should improve")
        self.assertLess(full_score_after[0], full_score_before[0], "Full score should improve")
    
    def test_multiple_judges_gap_scoring(self):
        """Test gap scoring with multiple judges."""
        print("\n=== Testing Multiple Judges Gap Scoring ===")
        
        judges = [
            Judge(judge_id=1, characteristics={Attribute.STRAFFE}),
            Judge(judge_id=2, characteristics={Attribute.CIVIL})
        ]
        
        rooms = [
            Room(room_id=1, characteristics=set()),
            Room(room_id=2, characteristics=set())
        ]
        
        meetings = []
        cases = []
        for i in range(4):
            case = Case(case_id=i+1, characteristics={Attribute.STRAFFE if i < 2 else Attribute.CIVIL})
            cases.append(case)
            meeting = Meeting(
                meeting_id=i+1,
                meeting_duration=30,
                duration_of_stay=0,
                judge=None,
                room=None,
                case=case
            )
            case.meetings.append(meeting)
            meetings.append(meeting)
        
        schedule = Schedule(
            work_days=1,
            minutes_in_a_work_day=240,
            granularity=30,
            judges=judges,
            rooms=rooms,
            meetings=meetings,
            cases=cases
        )
        
        # Place meetings with gaps
        # Judge 1: meetings at slots 3 and 5 (gap at start and between)
        placements = [
            (meetings[0], judges[0], rooms[0], 3),
            (meetings[1], judges[0], rooms[0], 5),
            # Judge 2: meetings at slots 1 and 4 (no gap at start, gap between)
            (meetings[2], judges[1], rooms[1], 1),
            (meetings[3], judges[1], rooms[1], 4)
        ]
        
        for meeting, judge, room, slot in placements:
            meeting.judge = judge
            meeting.room = room
            app = Appointment(
                meeting=meeting,
                judge=judge,
                room=room,
                day=1,
                timeslot_in_day=slot
            )
            schedule.add_meeting_to_schedule(app)
        
        schedule.initialize_appointment_chains()
        
        # Initialize compatibility matrices
        parsed_data = {"cases": cases, "judges": judges, "rooms": rooms}
        initialize_compatibility_matricies(parsed_data)
        
        # Calculate gaps for each judge
        gaps_judge1 = calculate_gaps_between_appointments(schedule, judges[0].judge_id)
        gaps_judge2 = calculate_gaps_between_appointments(schedule, judges[1].judge_id)
        total_rule31 = nr31_distance_between_meetings_full(schedule)
        
        print(f"\nGap analysis:")
        print(f"  Judge 1 (meetings at 3,5): {gaps_judge1} gaps")
        print(f"  Judge 2 (meetings at 1,4): {gaps_judge2} gaps")
        print(f"  Total rule 31 score: {total_rule31}")
        
        # Verify
        self.assertEqual(gaps_judge1, 2, "Judge 1 should have 2 gaps (start + between)")
        self.assertEqual(gaps_judge2, 1, "Judge 2 should have 1 gap (between meetings)")
        self.assertEqual(total_rule31, 3, "Total should be sum of all gaps")


if __name__ == '__main__':
    unittest.main(verbosity=2)