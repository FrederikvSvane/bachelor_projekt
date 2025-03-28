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
        n_cases = 10
        n_judges = 5
        n_rooms = 5
        n_work_days = 5
        granularity = 5
        min_per_work_day = 390
        json = generate_test_data_parsed(n_cases=n_cases, n_judges=n_judges, n_rooms=n_rooms, work_days=n_work_days, granularity=granularity, min_per_work_day=min_per_work_day)
        initialize_compatibility_matricies(json)

        self.schedule = generate_schedule_using_double_flow(json)

        self.cases = self.schedule.get_all_cases()
        self.meetings = self.schedule.get_all_meetings()
        self.judges = self.schedule.get_all_judges()
        self.rooms = self.schedule.get_all_rooms() 
        self.compatible_judges = calculate_compatible_judges(self.meetings, self.judges)
        self.compatible_rooms = calculate_compatible_rooms(self.meetings, self.rooms)
    
    def test_nr29_room_stability_per_day(self):
        visualize(self.schedule)

        move: Move = generate_random_move(self.schedule, self.compatible_judges, self.compatible_rooms)
        delta = nr29_room_stability_per_day_delta(self.schedule, move)
        print(move)

        violations_before = nr29_room_stability_per_day_full(self.schedule)
        do_move(move, self.schedule)
        violations_after = nr29_room_stability_per_day_full(self.schedule)

        print(f"Violations before: {violations_before}")
        print(f"Violations after: {violations_after}")
        print(f"Delta: {delta}")

        self.assertEqual(violations_after - violations_before ,delta)

if __name__ == '__main__':
    unittest.main()