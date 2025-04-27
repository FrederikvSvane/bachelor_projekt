import unittest
from copy import deepcopy

# Assuming imports are correctly handled relative to the project structure
# (Adjust imports based on actual project structure if needed)
from src.base_model.schedule import Schedule, generate_schedule_using_double_flow
from src.base_model.compatibility_checks import initialize_compatibility_matricies, calculate_compatible_judges, calculate_compatible_rooms
from src.local_search.rules_engine import calculate_full_score
from src.util.data_generator import generate_test_data_parsed
from src.local_search.move import do_move
from src.local_search.move_generator import generate_specific_delete_move, generate_specific_insert_move
from src.local_search.rules_engine import calculate_delta_score, calculate_full_score
from src.util.schedule_visualizer import visualize
from src.local_search.ruin_and_recreate import apply_ruin_and_recreate, RRStrategy
# Construction heuristic might be needed if generate_schedule_using_double_flow isn't sufficient
from src.construction.heuristic.linear_assignment import generate_schedule


class TestRuinAndRecreate(unittest.TestCase):

    def setUp(self):
        # Generate a small test schedule
        n_cases = 20
        n_judges = 4
        n_rooms = 8
        n_work_days = 2
        granularity = 5
        min_per_work_day = 390

        # Create test data and initial schedule using a heuristic
        self.test_data = generate_test_data_parsed(
            n_cases=n_cases,
            n_judges=n_judges,
            n_rooms=n_rooms,
            work_days=n_work_days,
            granularity=granularity,
            min_per_work_day=min_per_work_day
        )

        initialize_compatibility_matricies(self.test_data)
        # Using the heuristic construction method as an example
        self.schedule = generate_schedule_using_double_flow(self.test_data)
        self.schedule.move_all_dayboundary_violations()
        self.schedule.trim_schedule_length_if_possible()

        # Calculate compatibility matrices
        meetings = self.schedule.get_all_meetings() # Get all meetings (planned + unplanned initially)
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
        if len(planned_meetings) < 10:
            self.skipTest("Not enough planned meetings to test") 

        meetings_to_delete = planned_meetings[:10] 
        visualize(schedule_copy)

        for i, meeting in enumerate(meetings_to_delete): 
            # Create delete move
            delete_move = generate_specific_delete_move(schedule_copy, meeting.meeting_id) 

            # Calculate score before delete
            score_before = calculate_full_score(schedule_copy) 

            # Calculate delta score
            delta_score = calculate_delta_score(schedule_copy, delete_move) 

            # Apply delete move
            do_move(delete_move, schedule_copy) 

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

        visualize(schedule_copy)
    def test_insert_move_score_calculation(self):
        """Test that delta scores match full score differences for insert moves."""

        # Clone the schedule for testing
        schedule_copy = deepcopy(self.schedule) 
        visualize(schedule_copy)
        # First, delete some meetings to have unplanned meetings
        planned_meetings = schedule_copy.get_all_planned_meetings() 
        if len(planned_meetings) < 10: 
            self.skipTest("Not enough planned meetings to test") 

        meetings_to_process = planned_meetings[:10] 

        # Delete the meetings
        for meeting in meetings_to_process: 
            delete_move = generate_specific_delete_move(schedule_copy, meeting.meeting_id) 
            do_move(delete_move, schedule_copy) 

        visualize(schedule_copy)
        
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

        visualize(schedule_copy)

    def test_ruin_and_recreate_process(self):
        """Tests the ruin and recreate process by comparing scores and printing schedules."""
        print("\n--- Testing Ruin and Recreate Process ---")

        # Clone the schedule to avoid modifying the original setUp schedule
        schedule_copy = deepcopy(self.schedule) 

        # 1. Get and print the initial score
        initial_score = calculate_full_score(schedule_copy) 
        print(f"\nInitial Score: {initial_score}")

        # 2. Print the initial schedule
        print("\nSchedule Before Ruin and Recreate:")
        visualize(schedule_copy) 

        # 3. Apply Ruin and Recreate
        # Using RANDOM_MEETINGS strategy with 30% removal as an example
        strategy_to_use = RRStrategy.RANDOM_MEETINGS 
        percentage_to_remove = 30
        print(f"\nApplying Ruin and Recreate (Strategy: {strategy_to_use.value}, Percentage: {percentage_to_remove}%)...")

        success, num_inserted = apply_ruin_and_recreate(
            schedule=schedule_copy,
            compatible_judges_dict=self.compatible_judges, 
            compatible_rooms_dict=self.compatible_rooms, 
            strategy=strategy_to_use, 
            percentage=percentage_to_remove
        ) 

        if success:
            print(f"Ruin and Recreate successful. {num_inserted} meetings were re-inserted.")
        else:
            print("Ruin and Recreate did not result in any changes or insertions.")

        # 4. Get and print the final score
        final_score = calculate_full_score(schedule_copy) 
        print(f"\nFinal Score: {final_score}")

        # 5. Print the final schedule
        print("\nSchedule After Ruin and Recreate:")
        visualize(schedule_copy) 

        # 6. Compare scores (by printing)
        print(f"\nScore Comparison: Initial={initial_score}, Final={final_score}")
        print("--- End of Ruin and Recreate Test ---")

        # Optional: Add an assertion if needed, e.g., checking if the score changed
        # self.assertNotEqual(initial_score, final_score, "Score should ideally change after R&R")
        # Or check if the schedule remains valid, etc. For now, just printing as requested.


if __name__ == "__main__":
    # Note: Running this directly might require adjustments to imports
    # if run from a different directory context than the main project runner.
    unittest.main()