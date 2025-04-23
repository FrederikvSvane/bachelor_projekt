import unittest
from copy import deepcopy

from src.base_model.schedule import Schedule, generate_schedule_using_double_flow
from src.base_model.compatibility_checks import initialize_compatibility_matricies, calculate_compatible_judges, calculate_compatible_rooms
from src.local_search.rules_engine import calculate_full_score
from src.util.data_generator import generate_test_data_parsed
from src.local_search.move import do_move
from src.local_search.move_generator import generate_specific_delete_move, generate_specific_insert_move
from src.local_search.rules_engine import calculate_delta_score, calculate_full_score
from src.util.schedule_visualizer import visualize


class TestRuinAndRecreate(unittest.TestCase):
    
    def setUp(self):
        # Generate a small test schedule
        n_cases = 2
        n_judges = 3
        n_rooms = 3
        n_work_days = 1
        granularity = 5
        min_per_work_day = 390
        
        # Create test data and initial schedule
        self.test_data = generate_test_data_parsed(
            n_cases=n_cases, 
            n_judges=n_judges, 
            n_rooms=n_rooms, 
            work_days=n_work_days, 
            granularity=granularity, 
            min_per_work_day=min_per_work_day
        )
        
        initialize_compatibility_matricies(self.test_data)
        self.schedule = generate_schedule_using_double_flow(self.test_data)
        self.schedule.move_all_dayboundary_violations()
        self.schedule.trim_schedule_length_if_possible()
        
        # Calculate compatibility matrices
        meetings = self.schedule.get_all_planned_meetings()
        judges = self.schedule.get_all_judges()
        rooms = self.schedule.get_all_rooms()
        self.compatible_judges = calculate_compatible_judges(meetings, judges)
        self.compatible_rooms = calculate_compatible_rooms(meetings, rooms)
    
    
    def test_delete_move_score_calculation(self):
        """Test that delta scores match full score differences for delete moves."""
        
        # Clone the schedule for testing
        schedule_copy = deepcopy(self.schedule)
        
        # Get a few meetings to delete
        planned_meetings = schedule_copy.get_all_planned_meetings()
        if len(planned_meetings) < 3:
            self.skipTest("Not enough planned meetings to test")
        
        meetings_to_delete = planned_meetings[:3]
        
        for i, meeting in enumerate(meetings_to_delete):
            # Create delete move
            delete_move = generate_specific_delete_move(schedule_copy, meeting.meeting_id)
            
            # Calculate score before delete
            score_before = calculate_full_score(schedule_copy)
            
            # Calculate delta score
            delta_score = calculate_delta_score(schedule_copy, delete_move)
            
            visualize(schedule_copy)
            
            # Apply delete move
            print(delete_move)
            do_move(delete_move, schedule_copy)
            
            visualize(schedule_copy)
            # Calculate score after delete
            score_after = calculate_full_score(schedule_copy)
            
            # Calculate actual score difference
            actual_difference = score_after - score_before
            
            print(f"\nDelete move test {i+1}:")
            print(f"  Meeting ID: {meeting.meeting_id}")
            print(f"  Score before: {score_before}")
            print(f"  Score after: {score_after}")
            print(f"  Delta score: {delta_score}")
            print(f"  Actual difference: {actual_difference}")
            
            # Assert that delta score equals the actual score difference
            self.assertEqual(delta_score, actual_difference,
                          f"Delta score ({delta_score}) should equal actual score difference ({actual_difference})")
    
    def test_insert_move_score_calculation(self):
        """Test that delta scores match full score differences for insert moves."""
        
        # Clone the schedule for testing
        schedule_copy = deepcopy(self.schedule)
        
        # First, delete some meetings to have unplanned meetings
        planned_meetings = schedule_copy.get_all_planned_meetings()
        if len(planned_meetings) < 3:
            self.skipTest("Not enough planned meetings to test")
        
        meetings_to_process = planned_meetings[:3]
        
        # Delete the meetings
        for meeting in meetings_to_process:
            delete_move = generate_specific_delete_move(schedule_copy, meeting.meeting_id)
            do_move(delete_move, schedule_copy)
        
        # Verify we have unplanned meetings to work with
        unplanned_meetings = schedule_copy.get_all_unplanned_meetings()
        self.assertGreaterEqual(len(unplanned_meetings), 1, "Should have unplanned meetings to test insert")
        
        # Try to insert each unplanned meeting
        for i, meeting in enumerate(unplanned_meetings):
            # Find compatible resources
            compatible_judges = self.compatible_judges.get(meeting.meeting_id, [])
            compatible_rooms = self.compatible_rooms.get(meeting.meeting_id, [])
            
            if not compatible_judges or not compatible_rooms:
                print(f"Skipping meeting {meeting.meeting_id} - no compatible resources")
                continue
            
            # Pick a simple insertion point
            judge = compatible_judges[0]
            room = compatible_rooms[0]
            day = 1
            timeslot = (i * 5) + 1  # Spread meetings out to avoid conflicts
            
            # Create insert move
            insert_move = generate_specific_insert_move(
                schedule_copy, meeting, judge, room, day, timeslot
            )
            
            # Calculate score before insert
            score_before = calculate_full_score(schedule_copy)
            
            # Calculate delta score
            delta_score = calculate_delta_score(schedule_copy, insert_move)
            
            # Apply insert move
            do_move(insert_move, schedule_copy)
            
            # Calculate score after insert
            score_after = calculate_full_score(schedule_copy)
            
            # Calculate actual score difference
            actual_difference = score_after - score_before
            
            print(f"\nInsert move test {i+1}:")
            print(f"  Meeting ID: {meeting.meeting_id}")
            print(f"  Judge: {judge.judge_id}, Room: {room.room_id}")
            print(f"  Day: {day}, Timeslot: {timeslot}")
            print(f"  Score before: {score_before}")
            print(f"  Score after: {score_after}")
            print(f"  Delta score: {delta_score}")
            print(f"  Actual difference: {actual_difference}")
            
            # Assert that delta score equals the actual score difference
            self.assertEqual(delta_score, actual_difference,
                          f"Delta score ({delta_score}) should equal actual score difference ({actual_difference})")


if __name__ == "__main__":
    unittest.main()