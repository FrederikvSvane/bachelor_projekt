import unittest
import os
import time
import itertools
import multiprocessing
from typing import Callable, List, Tuple, Optional
from src.base_model.appointment import Appointment
from src.base_model.schedule import Schedule, generate_schedule_using_double_flow
from src.local_search.move import Move, do_move, undo_move
from src.util.schedule_visualizer import visualize
from copy import deepcopy
from src.local_search.rules_engine import *
import random

from src.util.data_generator import generate_test_data_parsed
from src.base_model.compatibility_checks import initialize_compatibility_matricies, calculate_compatible_judges, calculate_compatible_rooms
from src.local_search.move_generator import generate_compound_move, generate_random_delete_move, generate_random_move_of_random_type
from src.local_search.simulated_annealing import _calculate_moves_in_parallel
from src.construction.heuristic.linear_assignment import generate_schedule



class TestRulesEngine(unittest.TestCase):
    
    def setUp(self):
        #generate a random schedule for every test
        n_cases = 50
        n_judges = 5
        n_rooms = 5
        n_work_days = 2
        granularity = 5
        min_per_work_day = 390
        json = generate_test_data_parsed(n_cases=n_cases, n_judges=n_judges, n_rooms=n_rooms, work_days=n_work_days, granularity=granularity, min_per_work_day=min_per_work_day)
        initialize_compatibility_matricies(json)

        self.schedule = generate_schedule(json)
        self.schedule.initialize_appointment_chains()
        self.schedule.move_all_dayboundary_violations()
        self.schedule.trim_schedule_length_if_possible()

        self.cases = self.schedule.get_all_cases()
        self.meetings = self.schedule.get_all_meetings()
        self.judges = self.schedule.get_all_judges()
        self.rooms = self.schedule.get_all_rooms() 
        self.compatible_judges = calculate_compatible_judges(self.meetings, self.judges)
        self.compatible_rooms = calculate_compatible_rooms(self.meetings, self.rooms)
        
        self.rule_functions = [
            (nr1_overbooked_room_in_timeslot_delta, nr1_overbooked_room_in_timeslot_full),
            (nr2_overbooked_judge_in_timeslot_delta, nr2_overbooked_judge_in_timeslot_full),
            (nr6_virtual_room_must_have_virtual_meeting_delta, nr6_virtual_room_must_have_virtual_meeting_full),
            (nr8_judge_skillmatch_delta, nr8_judge_skillmatch_full),
            (nr14_virtual_case_has_virtual_judge_delta, nr14_virtual_case_has_virtual_judge_full),
            (nr18_unused_timegrain_delta, nr18_unused_timegrain_full),
            (nr19_case_has_specific_judge_delta, nr19_case_has_specific_judge_full),
            (nr20_max_weekly_coverage_delta, nr20_max_weekly_coverage_full),
            (nr21_all_meetings_planned_for_case_delta, nr21_all_meetings_planned_for_case_full),
            (nr29_room_stability_per_day_delta, nr29_room_stability_per_day_full),
            (nr31_distance_between_meetings_delta, nr31_distance_between_meetings_full),
        ]

    def test_full_score_vs_delta_score_and_move_reversibility(self):
        """
        Tests if delta score matches full score difference
        and if undo_move correctly reverts the schedule state over multiple iterations.
        """
        iterations = 100

        for i in range(iterations):
            schedule_initial = deepcopy(self.schedule)
            full_score_initial = calculate_full_score(self.schedule)
            
            move: Move = generate_random_move_of_random_type(self.schedule, self.compatible_judges, self.compatible_rooms)
            delta_score = calculate_delta_score(self.schedule, move)
            do_move(move, self.schedule)
            
            full_score_after_do = calculate_full_score(self.schedule)
            score_diff = full_score_after_do - full_score_initial
            self.assertEqual(score_diff, delta_score, f"Iteration {i}: Delta score ({delta_score}) != Full score difference ({score_diff}). Move: {move}")

            undo_move(move, self.schedule)
            
            full_score_after_do_undo = calculate_full_score(self.schedule)
            schedule_after_do_undo = deepcopy(self.schedule)
            self.assertEqual(full_score_initial, full_score_after_do_undo, f"Iteration {i+1}: Full score not restored after undo ({full_score_initial} -> {full_score_after_do} -> {full_score_after_do_undo}). Move: {move}")
            self.assertEqual(schedule_initial, schedule_after_do_undo, f"Iteration {i+1}: Schedules differs after undo. Move: {move}")
         
    def _check_delta_function_correctness(self, 
                                       delta_function: Callable, 
                                       full_function: Callable,
                                       schedule: Optional[Schedule] = None,
                                       compatible_judges: Optional[List] = None,
                                       compatible_rooms: Optional[List] = None):

            # Use provided parameters or fall back to instance variables
        schedule = schedule or self.schedule
        compatible_judges = compatible_judges or self.compatible_judges
        compatible_rooms = compatible_rooms or self.compatible_rooms
        
        # move = generate_single_random_move(schedule, compatible_judges, compatible_rooms)
        
        delete_move = generate_random_delete_move(schedule)
        do_move(delete_move, schedule) # we delete a meeting to facilitate a potential insert move
        
        
        move = generate_random_move_of_random_type(schedule, compatible_judges, compatible_rooms)
                
        violations_before = full_function(schedule)
        delta = delta_function(schedule, move)
        
        do_move(move, schedule)
        
        violations_after = full_function(schedule)
        
        undo_move(move, schedule)
        
        self.assertEqual(violations_after - violations_before, delta, 
                         f"Delta function {delta_function.__name__} failed: expected {violations_after - violations_before}, got {delta}")

    
    def test_all_delta_functions(self):
        """Test all delta functions against their corresponding full functions."""
        for delta_function, full_function in self.rule_functions:
            #with self.subTest(delta_function=delta_function.__name__):
            self._check_delta_function_correctness(delta_function, full_function)
    
    # Individual test methods for better test isolation
    def test_nr1_overbooked_room_in_timeslot(self):
        self._check_delta_function_correctness(
            nr1_overbooked_room_in_timeslot_delta,
            nr1_overbooked_room_in_timeslot_full
        )
    
    def test_nr2_overbooked_judge_in_timeslot(self):
        self._check_delta_function_correctness(
            nr2_overbooked_judge_in_timeslot_delta,
            nr2_overbooked_judge_in_timeslot_full
        )
    
    # Additional individual test methods for each rule
    def test_nr6_virtual_room_must_have_virtual_meeting(self):
        self._check_delta_function_correctness(
            nr6_virtual_room_must_have_virtual_meeting_delta,
            nr6_virtual_room_must_have_virtual_meeting_full
        )
    
    def test_nr8_judge_skillmatch(self):
        self._check_delta_function_correctness(
            nr8_judge_skillmatch_delta,
            nr8_judge_skillmatch_full
        )
    
    def test_nr14_virtual_case_has_virtual_judge(self):
        self._check_delta_function_correctness(
            nr14_virtual_case_has_virtual_judge_delta,
            nr14_virtual_case_has_virtual_judge_full
        )
    
    def test_nr18_unused_timegrain(self):
        self._check_delta_function_correctness(
            nr18_unused_timegrain_delta,
            nr18_unused_timegrain_full
        )
        
    def test_nr27_overdue_case_not_planned(self):
        self._check_delta_function_correctness(
            nr27_overdue_case_not_planned_delta,
            nr27_overdue_case_not_planned_full
        )
    
    def test_nr29_room_stability_per_day(self):
        self._check_delta_function_correctness(
            nr29_room_stability_per_day_delta,
            nr29_room_stability_per_day_full
        )
    
    def test_nr31_distance_between_meetings(self):
        self._check_delta_function_correctness(
            nr31_distance_between_meetings_delta,
            nr31_distance_between_meetings_full
        )
        
        


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
        
        
if __name__ == '__main__':
    unittest.main()