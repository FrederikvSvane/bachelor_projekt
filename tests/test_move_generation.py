import unittest

from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.appointment import Appointment
from src.base_model.schedule import Schedule
from src.local_search.simulated_annealing import (
    identify_appointment_chains,
    find_swap_moves
)
from src.base_model.attribute_enum import Attribute

from src.util.schedule_visualizer import visualize


class TestMoveGeneration(unittest.TestCase):
    
    def setUp(self):
        """
        setting up a simple schedule for reuse
        """
        
        self.schedule = Schedule(work_days=1, minutes_in_a_work_day=390, granularity=5)
        
        self.case1 = Case(case_id=1, case_duration=60, characteristics={Attribute.CIVIL}, judge_requirements={Attribute.CIVIL})
        self.case2 = Case(case_id=2, case_duration=120, characteristics={Attribute.STRAFFE}, judge_requirements={Attribute.STRAFFE})
        self.judge1 = Judge(judge_id=1, characteristics={Attribute.CIVIL})
        self.judge2 = Judge(judge_id=2, characteristics={Attribute.STRAFFE})
        self.room1 = Room(room_id=1)
        self.room2 = Room(room_id=2)
        
        self.case1_timeslots = self.case1.case_duration // self.schedule.granularity
        self.case2_timeslots = self.case2.case_duration // self.schedule.granularity
        
        self.app1 = [Appointment(self.case1, self.judge1, self.room1, 0, t, 1) for t in range(self.case1_timeslots + 1)]  # + 1 because range is exclusive
        self.app2 = [Appointment(self.case2, self.judge2, self.room2, 0, t, 1) for t in range(self.case2_timeslots + 1)]
        
        self.schedule.appointments.extend(self.app1)
        self.schedule.appointments.extend(self.app2)
    
    def test_identify_appointment_chains(self):
        chains = identify_appointment_chains(self.schedule)
        
        self.assertEqual(len(chains), 2, "Should identify 2 appointment chains")

        key1 = (1, 1, 1)  # (case_id, judge_id, room_id)
        self.assertIn(key1, chains, "Chain for case1-judge1-room1 missing")
        self.assertEqual(len(chains[key1]), self.case1_timeslots+1, "Chain for case1 should have 13 appointments")
        
        key2 = (2, 2, 2)  
        self.assertIn(key2, chains, "Chain for case2-judge2-room2 missing")
        self.assertEqual(len(chains[key2]), self.case2_timeslots+1, "Chain for case2 should have 26 appointments")
    
    def test_find_swap_moves(self):
        """Test finding swap moves between appointment chains"""
        swap_moves = find_swap_moves(self.schedule)
        
        # Should be 2 swap moves (swapping chain1 with chain2 and vice versa)
        self.assertEqual(len(swap_moves), 2, "Should find 2 swap moves")
        
        # Verify each move swaps different chains
        for move in swap_moves:
            # Chains should be different
            self.assertNotEqual(
                move.appointment1[0].case.case_id,
                move.appointment2[0].case.case_id,
                "Swap move should swap different case chains"
            )