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

from src.util.calendar_visualizer import generate_calendar


class TestMoveGeneration(unittest.TestCase):
    
    def setUp(self):
        """Set up a simple schedule for testing"""
        # Create schedule
        self.schedule = Schedule(work_days=2, minutes_in_a_work_day=390, granularity=5)
        
        # Create cases
        self.case1 = Case(case_id=1, case_duration=60, characteristics={Attribute.CIVIL})
        self.case2 = Case(case_id=2, case_duration=120, characteristics={Attribute.STRAFFE})
        
        # Create judges
        self.judge1 = Judge(judge_id=1, characteristics={Attribute.CIVIL})
        self.judge2 = Judge(judge_id=2, characteristics={Attribute.STRAFFE, Attribute.CIVIL})
        
        # Create rooms
        self.room1 = Room(room_id=1)
        self.room2 = Room(room_id=2)
        
        # Add appointments - case1 spans 2 timeslots
        self.app1_1 = Appointment(self.case1, self.judge1, self.room1, 0, 0, 1)
        self.app1_2 = Appointment(self.case1, self.judge1, self.room1, 0, 1, 1)
        
        # Case2 is on a different day
        self.app2 = Appointment(self.case2, self.judge2, self.room2, 1, 0, 2)
        
        # Add to schedule
        self.schedule.appointments = [self.app1_1, self.app1_2, self.app2]
    
    def test_identify_appointment_chains(self):
        """Test identifying chains of appointments"""

        generate_calendar(self.schedule)
        
        chains = identify_appointment_chains(self.schedule)
        
        # Should have 2 chains
        self.assertEqual(len(chains), 2, "Should identify 2 appointment chains")
        
        # First chain should be for case1, judge1, room1 with 2 appointments
        key1 = (1, 1, 1)  # (case_id, judge_id, room_id)
        self.assertIn(key1, chains, "Chain for case1-judge1-room1 missing")
        self.assertEqual(len(chains[key1]), 2, "Chain for case1 should have 2 appointments")
        
        # Second chain should be for case2, judge2, room2 with 1 appointment
        key2 = (2, 2, 2)  # (case_id, judge_id, room_id)
        self.assertIn(key2, chains, "Chain for case2-judge2-room2 missing")
        self.assertEqual(len(chains[key2]), 1, "Chain for case2 should have 1 appointment")
    
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