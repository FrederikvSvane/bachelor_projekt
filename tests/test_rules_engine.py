import unittest
from src.base_model.appointment import Appointment
from src.base_model.schedule import Schedule
from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.local_search.move import Move, apply_move_to_schedule
from src.util.schedule_visualizer import visualize
from src.util.parser import parse_input
from src.local_search.rules_engine import room_stability_per_day_full, room_stability_per_day_delta, count_room_changes_for_judge_on_specific_day

def get_appointments_for_case(self, case):
    return [a for a in self.schedule.appointments if a.case == case]

def add_appointments_for_case(self, case, judge, room, day, start_timeslot):
    for t in range(case.case_duration // self.schedule.granularity):
        self.schedule.appointments.append(Appointment(case, judge, room, day, start_timeslot + t))

def initialize_quality_test(self):
    parsed_data = parse_input("quality_test.json")
    cases = parsed_data["cases"]
    judges = parsed_data["judges"]
    rooms = parsed_data["rooms"]
    
    assignments = [
        (0, 0, range(0, 6)),    # Judge 0, Room 0, Cases 0-5
        (1, 1, range(6, 13)),   # Judge 1, Room 1, Cases 6-12
        (2, 2, range(13, 20))   # Judge 2, Room 2, Cases 13-19
    ]
    
    for judge_idx, room_idx, case_indices in assignments:
        judge = judges[judge_idx]
        room = rooms[room_idx]
        day = 1 
        current_time = 1  
        
        for case_idx in case_indices:
            case = cases[case_idx]
            slots_needed = case.case_duration // self.schedule.granularity
            
            for slot in range(slots_needed):
                appointment = Appointment(
                    case,
                    judge,
                    room,
                    day,
                    current_time + slot
                )
                self.schedule.appointments.append(appointment)
            
            current_time += slots_needed

class TestRoomStabilityRule(unittest.TestCase):
    
    def setUp(self):
        self.schedule = Schedule(2, 390, 5)
        
        self.judge1 = Judge(1)
        self.judge2 = Judge(2)
        
        self.room1 = Room(1)
        self.room2 = Room(2)
        self.room3 = Room(3)
        
        self.case1 = Case(1, 30)
        self.case2 = Case(2, 30)
        self.case3 = Case(3, 30)
        self.case4 = Case(4, 30)
        self.case5 = Case(5, 30)
        self.case6 = Case(6, 30)
    
# FULL score calculations

    def test_no_room_changes(self):
        add_appointments_for_case(self, self.case1, self.judge1, self.room1, 1, 1)
        add_appointments_for_case(self, self.case2, self.judge1, self.room1, 1, 8)
                
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 0, "violations should be 0 when judge stays in the same room")
    
    def test_two_room_changes(self):
        add_appointments_for_case(self, self.case1, self.judge1, self.room1, 1, 1)
        add_appointments_for_case(self, self.case2, self.judge1, self.room2, 1, 8) # changes both ways
        add_appointments_for_case(self, self.case3, self.judge1, self.room1, 1, 15)
        
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 2, "violations should be 2 when judge changes room twice")
    
    def test_full_quality_test(self):
        initialize_quality_test(self)
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 0, "violations should be 0 for the full quality test")
    
# DELTA score calculations

    def simple_multiple_moves_scenario(self):
        add_appointments_for_case(self, self.case1, self.judge1, self.room1, 1, 1)
        add_appointments_for_case(self, self.case2, self.judge1, self.room2, 1, 8)
        add_appointments_for_case(self, self.case3, self.judge2, self.room1, 1, 1)
        add_appointments_for_case(self, self.case4, self.judge2, self.room2, 1, 8)
        
        # assert full score is 2
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 2)
        
        # move case 1 to judge 2 timslot 14 => assert full score is 2 and delta score is 0)
        appointments = get_appointments_for_case(self, self.case1)
        move = Move(case_id = 1, appointments = appointments, old_judge= self.judge1, new_judge= self.judge2, old_room= self.room1, new_room= self.room1, old_day= 1, new_day= 1, old_start_timeslot= 1, new_start_timeslot= 14)
        apply_move_to_schedule(self.schedule, move)

        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 2)
        
        # now move case 4 to judge 1 timeslot 1 => assert full score is 0 and delta score is -2
        appointments = get_appointments_for_case(self, self.case4)
        move = Move(case_id = 4, appointments = appointments, old_judge= self.judge2, new_judge= self.judge1, old_room= self.room2, new_room=None, old_day= 1, new_day=None, old_start_timeslot= 8, new_start_timeslot= None)
        delta = room_stability_per_day_delta(self.schedule, move)
        self.assertEqual(delta, -2)

        apply_move_to_schedule(self.schedule, move)
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 0)
        
    def test_day_change_only(self):
        """Test delta calculation when only changing day assignment"""
        # Setup judge1 with cases on days 1 and 2, with room changes on both days
        add_appointments_for_case(self, self.case1, self.judge1, self.room2, 1, 8)
        add_appointments_for_case(self, self.case2, self.judge1, self.room1, 1, 15)
        add_appointments_for_case(self, self.case3, self.judge1, self.room1, 2, 1)
        add_appointments_for_case(self, self.case4, self.judge1, self.room2, 2, 8)
        
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 2, "Initial violations should be 2")
        
        # Move case2 to day 2 - this reduces violations by 1 on day 1 but increases them by 1 on day 2
        appointments = get_appointments_for_case(self, self.case2)
        move = Move(case_id=2, appointments=appointments, 
                    old_judge=self.judge1, new_judge=None, 
                    old_room=self.room1, new_room=None,
                    old_day=1, new_day=2, 
                    old_start_timeslot=15, new_start_timeslot=None)
        
        delta = room_stability_per_day_delta(self.schedule, move)
        apply_move_to_schedule(self.schedule, move)
        self.assertEqual(delta, 0, "Delta should be 0 as we're removing 1 violation from day 1 but adding 1 to day 2")
        
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 2, "Final violations should still be 2")
    
    def test_judge_change_only(self):
        """Test delta calculation when only changing judge assignment"""
        # Judge1 has cases 1 & 2 with a room change
        # Judge2 has cases 3 & 4 with a room change
        # Total violations = 2
        add_appointments_for_case(self, self.case1, self.judge1, self.room1, 1, 15)
        add_appointments_for_case(self, self.case2, self.judge1, self.room2, 1, 8)
        add_appointments_for_case(self, self.case3, self.judge2, self.room1, 1, 1)
        add_appointments_for_case(self, self.case4, self.judge2, self.room2, 1, 8)
        
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 2, "Initial violations should be 2")
        
        # Move case1 to judge2 
        appointments = get_appointments_for_case(self, self.case1)
        move = Move(case_id=1, appointments=appointments, 
                    old_judge=self.judge1, new_judge=self.judge2, 
                    old_room=self.room1, new_room=None,  
                    old_day=1, new_day=None,  
                    old_start_timeslot=15, new_start_timeslot=None)  
        
        delta = room_stability_per_day_delta(self.schedule, move)
        self.assertEqual(delta, 0, "Delta should be 0 as we're maintaining the same number of violations")
        
        apply_move_to_schedule(self.schedule, move)
        
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 2, "Final violations should still be 2")
    
    def test_room_change_only(self):
        """Test delta calculation when only changing room assignment"""
        # Setup judge1 with room change (room1 -> room2)
        add_appointments_for_case(self, self.case1, self.judge1, self.room1, 1, 1)
        add_appointments_for_case(self, self.case2, self.judge1, self.room2, 1, 8)
        
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 1, "Initial violations should be 1")
        
        # Move case2 to room1 - only changing room
        appointments = get_appointments_for_case(self, self.case2)
        move = Move(case_id=2, appointments=appointments, 
                    old_judge=self.judge1, new_judge=None,  # Not changing judge
                    old_room=self.room2, new_room=self.room1,
                    old_day=1, new_day=None,  # Not changing day
                    old_start_timeslot=8, new_start_timeslot=None)  # Not changing timeslot
        
        delta = room_stability_per_day_delta(self.schedule, move)
        self.assertEqual(delta, -1, "Delta should be -1 as we're removing 1 violation")
        
        apply_move_to_schedule(self.schedule, move)
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 0, "Final violations should be 0")
    
    def test_timeslot_change_only(self):
        """Test delta calculation when only changing timeslot assignment"""
        # Setup judge1 with room change (room1 -> room2)
        add_appointments_for_case(self, self.case1, self.judge1, self.room1, 1, 1)
        add_appointments_for_case(self, self.case2, self.judge1, self.room2, 1, 8)
        add_appointments_for_case(self, self.case3, self.judge1, self.room2, 1, 22)
        
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 1, "Initial violations should be 1")
        
        # Move case1 to timeslot between case2 and case3 - only changing timeslot
        appointments = get_appointments_for_case(self, self.case1)
        move = Move(case_id=1, appointments=appointments, 
                    old_judge=self.judge1, new_judge=None,  # Not changing judge
                    old_room=self.room1, new_room=None,  # Not changing room
                    old_day=1, new_day=None,  # Not changing day
                    old_start_timeslot=1, new_start_timeslot=15)  # Changing timeslot
        
        delta = room_stability_per_day_delta(self.schedule, move)
        self.assertEqual(delta, 1, "Delta should be 1 as we're adding a new room change")
        
        apply_move_to_schedule(self.schedule, move)
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 2, "Final violations should be 2")
        
    def test_multiple_parameter_changes(self):
        """Test delta calculation when changing multiple parameters simultaneously"""
        # Setup: judge1 has room change, judge2 has no room change
        add_appointments_for_case(self, self.case1, self.judge1, self.room1, day=1, start_timeslot=1)
        add_appointments_for_case(self, self.case2, self.judge1, self.room1, day=1, start_timeslot=8)
        add_appointments_for_case(self, self.case3, self.judge2, self.room2, day=1, start_timeslot=1)
        add_appointments_for_case(self, self.case4, self.judge2, self.room2, day=1, start_timeslot=8)
        add_appointments_for_case(self, self.case5, self.judge2, self.room3, day=2, start_timeslot=1)
        add_appointments_for_case(self, self.case6, self.judge2, self.room3, day=2, start_timeslot=15)
        
        visualize(self.schedule)
        
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 0, "Initial violations should be 0")
        
        # Move case2 to judge2, room1, day 2 - changing judge, room, day, and timeslot
        appointments = get_appointments_for_case(self, self.case1)
        move = Move(case_id=1, appointments=appointments, 
                    old_judge=self.judge1, new_judge=self.judge2, 
                    old_room=self.room1, new_room=self.room2,
                    old_day=1, new_day=2, 
                    old_start_timeslot=1, new_start_timeslot=8)
        
        delta = room_stability_per_day_delta(self.schedule, move)
        apply_move_to_schedule(self.schedule, move)
        visualize(self.schedule)
        self.assertEqual(delta, 2, "Delta should be 2 as we're removing 2 violation")
        
        
        violations = room_stability_per_day_full(self.schedule)
        self.assertEqual(violations, 2, "Final violations should be 2")
                
if __name__ == '__main__':
    unittest.main()