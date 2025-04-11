import unittest
import os
import time
import itertools
import multiprocessing
from src.base_model.appointment import Appointment
from src.base_model.schedule import Schedule, generate_schedule_using_double_flow
from src.local_search.move import Move, do_move, undo_move
from src.util.schedule_visualizer import visualize
from copy import deepcopy
from src.local_search.rules_engine import *

from src.util.data_generator import generate_test_data_parsed
from src.base_model.compatibility_checks import initialize_compatibility_matricies, calculate_compatible_judges, calculate_compatible_rooms
from src.local_search.move_generator import generate_single_move, generate_list_random_move
from src.local_search.simulated_annealing import _calculate_moves_in_parallel



class TestRulesEngine(unittest.TestCase):
    
    def setUp(self):
        #generate a random schedule for every test
        n_cases = 10
        n_judges = 5
        n_rooms = 5
        n_work_days = 2
        granularity = 5
        min_per_work_day = 390
        json = generate_test_data_parsed(n_cases=n_cases, n_judges=n_judges, n_rooms=n_rooms, work_days=n_work_days, granularity=granularity, min_per_work_day=min_per_work_day)
        initialize_compatibility_matricies(json)

        self.schedule = generate_schedule_using_double_flow(json)
        self.schedule.move_all_dayboundary_violations()
        self.schedule.trim_schedule_length_if_possible()

        self.cases = self.schedule.get_all_cases()
        self.meetings = self.schedule.get_all_meetings()
        self.judges = self.schedule.get_all_judges()
        self.rooms = self.schedule.get_all_rooms() 
        self.compatible_judges = calculate_compatible_judges(self.meetings, self.judges)
        self.compatible_rooms = calculate_compatible_rooms(self.meetings, self.rooms)

    # def test_full_score_vs_delta_score_and_move_reversibility(self):
    #     """
    #     Tests if delta score matches full score difference
    #     and if undo_move correctly reverts the schedule state over multiple iterations.
    #     """
    #     iterations = 100

    #     for i in range(iterations):
    #         schedule_initial = deepcopy(self.schedule)
    #         full_score_initial = calculate_full_score(self.schedule)
            
    #         move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
    #         delta_score = calculate_delta_score(self.schedule, move)
    #         do_move(move, self.schedule)
            
    #         full_score_after_do = calculate_full_score(self.schedule)
    #         score_diff = full_score_after_do - full_score_initial
    #         self.assertEqual(score_diff, delta_score, f"Iteration {i}: Delta score ({delta_score}) != Full score difference ({score_diff}). Move: {move}")

    #         undo_move(move, self.schedule)
    #         full_score_after_do_undo = calculate_full_score(self.schedule)
    #         schedule_after_do_undo = deepcopy(self.schedule)
    #         self.assertEqual(full_score_initial, full_score_after_do_undo, f"Iteration {i+1}: Full score not restored after undo ({full_score_initial} -> {full_score_after_do} -> {full_score_after_do_undo}). Move: {move}")
    #         self.assertEqual(schedule_initial, schedule_after_do_undo, f"Iteration {i+1}: Schedules differs after undo. Move: {move}")
         
        
    # def test_calculate_delta_in_parallel(self):
    #     """Tests if parallel delta score calculation matches sequential and compares timings."""
    #     test_schedule = deepcopy(self.schedule)
    #     initial_score = calculate_full_score(test_schedule)
    #     n_cores = os.cpu_count() if os.cpu_count() else 1

    #     list_of_move_lists = []
    #     # Generate 100 batches of moves (each batch is a list)
    #     for _ in range(10):
    #         generated_batch = generate_list_random_move(
    #             test_schedule,
    #             self.compatible_judges,
    #             self.compatible_rooms,
    #             [],
    #             initial_score,
    #             initial_score
    #         )
    #         # Append the generated list (batch) if it's not empty
    #         if generated_batch:
    #              list_of_move_lists.append(generated_batch)

    #     # --- Flatten the list of lists into a single list ---
    #     # Example: [[(m1,i1)], [(m2,i2), (m3,i3)]] -> [(m1,i1), (m2,i2), (m3,i3)]
    #     moves_with_gen_int = list(itertools.chain.from_iterable(list_of_move_lists))


    #     if not moves_with_gen_int:
    #          self.skipTest("No moves generated, cannot test parallel calculation.")
    #     with multiprocessing.Pool(processes=n_cores) as pool:
    #         parallel_results = []
            
    #         parallel_time = 0.0
    #         start_time_par = time.perf_counter()
        
    #         parallel_results = _calculate_moves_in_parallel(
    #             pool,
    #             test_schedule,
    #             moves_with_gen_int
    #         )
            
    #         end_time_par = time.perf_counter()
    #     parallel_time = end_time_par - start_time_par

    #     sequential_results = []
    #     sequential_time = 0.0
        
    #     start_time_seq = time.perf_counter()
    #     for move_obj, _ in moves_with_gen_int:
    #         sequential_score = calculate_delta_score(test_schedule, move_obj)
    #         sequential_results.append((move_obj, sequential_score))
    #     end_time_seq = time.perf_counter()
    #     sequential_time = end_time_seq - start_time_seq

    #     print(f"\n--- Timing Results ({len(moves_with_gen_int)} moves, {n_cores} cores) ---")
    #     print(f"Sequential Time: {sequential_time:.6f} seconds")
    #     print(f"Parallel Time:   {parallel_time:.6f} seconds")
        
    #     if parallel_time > 1e-9: # Avoid division by zero for very fast runs
    #          speedup = sequential_time / parallel_time
    #          print(f"Speedup Factor:  {speedup:.2f}x")
    #          if speedup < 1.0:
    #              print("(Note: Parallel was slower, likely due to overhead > calculation time)")
    #     else:
    #          print("Parallel time near zero; speedup calculation unreliable.")
    #     print("----------------------------------------")

    #     self.assertEqual(len(parallel_results), len(sequential_results),
    #                      f"Result counts differ: Parallel={len(parallel_results)}, Sequential={len(sequential_results)}")

    #     parallel_scores = [score for _, score in parallel_results]
    #     sequential_scores = [score for _, score in sequential_results]
    #     self.assertListEqual(parallel_scores, sequential_scores,
    #                          "Calculated scores mismatch between parallel and sequential execution.")

    #     parallel_move_ids = [m.meeting_id for m, _ in parallel_results]
    #     original_move_ids = [m.meeting_id for m, _ in moves_with_gen_int]
    #     self.assertListEqual(parallel_move_ids, original_move_ids,
    #                          "Move order/association mismatch (based on meeting_id).")
        
            
    def test_gap_in_schedule(self):
        move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
        
        delta = distance_between_meetings_delta(self.schedule, move)
        
        violations_before = distance_between_meetings_full(self.schedule)
        
        visualize(self.schedule)
        do_move(move, self.schedule)
        visualize(self.schedule)
        
        violations_after = distance_between_meetings_full(self.schedule)
        
        print(f"move: {move}")
        print(f"violations before: {violations_before}")
        print(f"violations after: {violations_after}")
        print(f"delta: {delta}")
        
        self.assertEqual(violations_after - violations_before ,delta)        
        
        
    # def test_nr1_overbooked_room_in_timeslot(self):
    #     move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
    #     delta = nr1_overbooked_room_in_timeslot_delta(self.schedule, move)
        
    #     violations_before = nr1_overbooked_room_in_timeslot_full(self.schedule)
        
    #     do_move(move, self.schedule)
        
    #     violations_after = nr1_overbooked_room_in_timeslot_full(self.schedule)
        
        
    #     self.assertEqual(violations_after - violations_before ,delta)
        
    
    # def test_nr2_overbooked_judge_in_timeslot(self):
    #     move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
    #     delta = nr2_overbooked_judge_in_timeslot_delta(self.schedule, move)
        
    #     violations_before = nr2_overbooked_judge_in_timeslot_full(self.schedule)
        
    #     do_move(move, self.schedule)
        
    #     violations_after = nr2_overbooked_judge_in_timeslot_full(self.schedule)
        
    #     self.assertEqual(violations_after - violations_before ,delta)
        
    # def test_nr6_virtual_room_must_have_virtual_meeting(self):
    #     move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
    #     delta = nr6_virtual_room_must_have_virtual_meeting_delta(self.schedule, move)
        
    #     violations_before = nr6_virtual_room_must_have_virtual_meeting_full(self.schedule)
        
    #     do_move(move, self.schedule)
        
    #     violations_after = nr6_virtual_room_must_have_virtual_meeting_full(self.schedule)
        
    #     self.assertEqual(violations_after - violations_before ,delta)
        
    # def test_nr_14_virtual_judge_must_have_virtual_meeting(self):
    #     move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
    #     delta = nr14_virtual_case_has_virtual_judge_delta(self.schedule, move)
        
    #     violations_before = nr14_virtual_case_has_virtual_judge_full(self.schedule)
        
    #     do_move(move, self.schedule)
        
    #     violations_after = nr14_virtual_case_has_virtual_judge_full(self.schedule)
        
    #     self.assertEqual(violations_after - violations_before ,delta)
    
    # def test_nr18_unused_timegrain(self):
    #     move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
    #     delta = nr18_unused_timegrain_delta(self.schedule, move)
        
    #     violations_before = nr18_unused_timegrain_full(self.schedule)
    #     do_move(move, self.schedule)
        
    #     violations_after = nr18_unused_timegrain_full(self.schedule)
        
    #     self.assertEqual(violations_after - violations_before ,delta)

    # def test_nr29_room_stability_per_day(self):
    #     move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
    #     delta = nr29_room_stability_per_day_delta(self.schedule, move)

    #     visualize(self.schedule)

    #     violations_before = nr29_room_stability_per_day_full(self.schedule)
    #     do_move(move, self.schedule)

    #     visualize(self.schedule)


    #     violations_after = nr29_room_stability_per_day_full(self.schedule)
        
    #     print(move)
    #     print(f"violations before: {violations_before}")
    #     print(f"violations after: {violations_after}")
    #     print(f"delta: {delta}")

    #     self.assertEqual(violations_after - violations_before ,delta)
        
if __name__ == '__main__':
    unittest.main()