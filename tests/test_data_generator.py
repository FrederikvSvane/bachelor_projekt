import unittest
from src.util.data_generator import generate_test_data_parsed
from src.base_model.compatibility_checks import case_requires_from_judge, judge_requires_from_case


class TestDataGenerator(unittest.TestCase):
    
    def test_generated_data_is_solvable(self):
        """
        Test that generated test data is fundamentally solvable.
        
        Every case must have at least one compatible judge.
        """
        # Generate test data with various configurations
        test_configs = [
            (5, 3, 2, 1),    # Small dataset: 5 cases, 3 judges, 2 rooms
            (10, 5, 3, 2),   # Medium dataset
            (20, 8, 5, 2),   # Larger dataset
        ]
        
        for n_cases, n_judges, n_rooms, n_days in test_configs:
            with self.subTest(f"Testing with {n_cases} cases, {n_judges} judges, {n_rooms} rooms"):
                # Generate data
                parsed_data = generate_test_data_parsed(n_cases, n_judges, n_rooms, n_days, granularity=5, min_per_work_day=390)
                
                cases = parsed_data["cases"]
                judges = parsed_data["judges"]
                
                # Check if each case has at least one compatible judge
                for case in cases:
                    compatible_judges = []
                    for judge in judges:
                        if case_requires_from_judge(case, judge) and judge_requires_from_case(judge, case):
                            compatible_judges.append(judge)
                    
                    case_req_str = ", ".join(str(attr) for attr in case.judge_requirements)
                    case_char_str = ", ".join(str(attr) for attr in case.characteristics)
                    
                    self.assertGreater(
                        len(compatible_judges), 0,
                        f"Case {case.case_id} has no compatible judges.\n"
                        f"Case requirements: [{case_req_str}]\n"
                        f"Case characteristics: [{case_char_str}]\n"
                        f"Judge capabilities:\n" + 
                        "\n".join([f"  Judge {j.judge_id}: chars={j.characteristics}, reqs={j.case_requirements}" 
                                  for j in judges])
                    )

                ###################################################
                ### Er slået fra for nu, loggikken er ikke klar ###
                ###################################################
                
                # # Also verify room compatibility
                # rooms = parsed_data["rooms"]
                # for case in cases:
                #     compatible_rooms = []
                #     for room in rooms:
                #         if (case_room_compatible(case, room)):
                #             compatible_rooms.append(room)
                    
                #     self.assertGreater(
                #         len(compatible_rooms), 0,
                #         f"Case {case.case_id} has no compatible rooms.\n"
                #         f"Room requirements: {room.case_requirements}\n"
                #         f"Case characteristics: {case.characteristics}\n"
                #         f"Case room requirements: {case.room_requirements}\n"
                #         f"Room capabilities: {room.characteristics}"
                #     )

    def test_judge_capacity_is_enough(self):
        """Test that the total judge capacity is sufficient for all cases."""
        n_cases, n_judges, n_rooms, n_days, granularity, min_per_work_day = 15, 5, 3, 2, 5, 390
        
        parsed_data = generate_test_data_parsed(n_cases, n_judges, n_rooms, n_days, granularity, min_per_work_day)
        cases = parsed_data["cases"]
        judges = parsed_data["judges"]
        
        meetings = []
        for case in cases:
            meetings.extend(case.meetings)
        
        # Import the capacity calculation function
        from src.base_model.capacity_calculator import calculate_all_judge_capacities
        
        capacities = calculate_all_judge_capacities(meetings, judges)
        total_capacity = sum(capacities.values())
        
        self.assertEqual(
            total_capacity, len(meetings),
            f"Total judge capacity ({total_capacity}) does not match number of cases ({len(cases)})"
        )
        
        # Check that each judge has a reasonable capacity
        for judge_id, capacity in capacities.items():
            self.assertGreaterEqual(
                capacity, 0,
                f"Judge {judge_id} has negative capacity: {capacity}"
            )

if __name__ == "__main__":
    unittest.main()