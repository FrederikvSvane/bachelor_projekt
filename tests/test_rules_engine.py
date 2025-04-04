import unittest
from src.base_model.appointment import Appointment
from src.base_model.schedule import Schedule, generate_schedule_using_double_flow
from src.local_search.move import Move
from src.util.schedule_visualizer import visualize
from src.local_search.rules_engine import *

from src.util.data_generator import generate_test_data_parsed
from src.base_model.compatibility_checks import initialize_compatibility_matricies, calculate_compatible_judges, calculate_compatible_rooms
from src.local_search.move_generator import generate_random_move



class TestRulesEngine(unittest.TestCase):
    
    def setUp(self):
        #generate a random schedule for every test
        n_cases = 8
        n_judges = 4
        n_rooms = 4
        n_work_days = 2
        granularity = 5
        min_per_work_day = 390
        json = generate_test_data_parsed(n_cases=n_cases, n_judges=n_judges, n_rooms=n_rooms, work_days=n_work_days, granularity=granularity, min_per_work_day=min_per_work_day)
        initialize_compatibility_matricies(json)

        self.schedule = generate_schedule_using_double_flow(json)
        self.schedule.move_all_dayboundary_violations()

        self.cases = self.schedule.get_all_cases()
        self.meetings = self.schedule.get_all_meetings()
        self.judges = self.schedule.get_all_judges()
        self.rooms = self.schedule.get_all_rooms() 
        self.compatible_judges = calculate_compatible_judges(self.meetings, self.judges)
        self.compatible_rooms = calculate_compatible_rooms(self.meetings, self.rooms)
    
        
    def test_nr1_overbooked_room_in_timeslot(self):
        move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
        delta = nr1_overbooked_room_in_timeslot_delta(self.schedule, move)
        
        violations_before = nr1_overbooked_room_in_timeslot_full(self.schedule)
        
        do_move(move, self.schedule)
        
        violations_after = nr1_overbooked_room_in_timeslot_full(self.schedule)
        
        
        self.assertEqual(violations_after - violations_before ,delta)
        
    
    def test_nr2_overbooked_judge_in_timeslot(self):
        move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
        delta = nr2_overbooked_judge_in_timeslot_delta(self.schedule, move)
        
        violations_before = nr2_overbooked_judge_in_timeslot_full(self.schedule)
        
        do_move(move, self.schedule)
        
        violations_after = nr2_overbooked_judge_in_timeslot_full(self.schedule)
        
        self.assertEqual(violations_after - violations_before ,delta)
        
    def test_nr6_virtual_room_must_have_virtual_meeting(self):
        move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
        delta = nr6_virtual_room_must_have_virtual_meeting_delta(self.schedule, move)
        
        violations_before = nr6_virtual_room_must_have_virtual_meeting_full(self.schedule)
        
        do_move(move, self.schedule)
        
        violations_after = nr6_virtual_room_must_have_virtual_meeting_full(self.schedule)
        
        self.assertEqual(violations_after - violations_before ,delta)
        
    def test_nr_14_virtual_judge_must_have_virtual_meeting(self):
        move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
        delta = nr14_virtual_case_has_virtual_judge_delta(self.schedule, move)
        
        violations_before = nr14_virtual_case_has_virtual_judge_full(self.schedule)
        
        do_move(move, self.schedule)
        
        violations_after = nr14_virtual_case_has_virtual_judge_full(self.schedule)
        
        self.assertEqual(violations_after - violations_before ,delta)
    
    def test_nr18_unused_timegrain(self):
        move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
        delta = nr18_unused_timegrain_delta(self.schedule, move)
        
        violations_before = nr18_unused_timegrain_full(self.schedule)
        do_move(move, self.schedule)
        
        violations_after = nr18_unused_timegrain_full(self.schedule)
        
        self.assertEqual(violations_after - violations_before ,delta)

    def test_nr29_room_stability_per_day(self):
        move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
        delta = nr29_room_stability_per_day_delta(self.schedule, move)

        visualize(self.schedule)

        violations_before = nr29_room_stability_per_day_full(self.schedule)
        do_move(move, self.schedule)

        visualize(self.schedule)


        violations_after = nr29_room_stability_per_day_full(self.schedule)
        
        print(move)
        print(f"violations before: {violations_before}")
        print(f"violations after: {violations_after}")
        print(f"delta: {delta}")

        self.assertEqual(violations_after - violations_before ,delta)
        
if __name__ == '__main__':
    unittest.main()