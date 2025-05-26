import unittest

from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.attribute_enum import Attribute
from src.base_model.meeting import Meeting
from src.base_model.capacity_calculator import calculate_all_room_capacities
from src.construction.graph.graph import MeetingJudgeNode


class TestRoomCapacityCalculation(unittest.TestCase):
    
    def test_room_capacity_calculation_distributes_all_pairs(self):
        """
        Test that room capacity calculation correctly distributes all judge-meeting pairs.
        This test aims to reproduce and fix the issue where assigned capacity exceeds total pairs.
        
        The warning: "Room capacity calculation did not distribute all pairs. Assigned: 105, Total: 100"
        indicates that the fractional assignment logic is double-counting some pairs.
        """
        # Create rooms with different characteristics
        rooms = [
            Room(room_id=1, characteristics=set()),  # Generic room - can handle all
            Room(room_id=2, characteristics={Attribute.SECURITY}),  # Security room
            Room(room_id=3, characteristics={Attribute.VIRTUAL}),  # Virtual room
            Room(room_id=4, characteristics={Attribute.SECURITY, Attribute.VIRTUAL})  # Both
        ]
        
        # Create judges
        judges = [
            Judge(judge_id=1, characteristics={Attribute.STRAFFE}),
            Judge(judge_id=2, characteristics={Attribute.CIVIL}),
            Judge(judge_id=3, characteristics={Attribute.TVANG})
        ]
        
        # Create 100 judge-meeting pairs with varied requirements
        jm_pairs = []
        
        # 40 pairs with no room requirements (can go to any room)
        for i in range(40):
            case = Case(case_id=i, characteristics={Attribute.STRAFFE})
            case.room_requirements = set()
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=30,
                duration_of_stay=0,
                judge=judges[i % 3],
                room=None,
                case=case
            )
            judges[i % 3].room_requirements = set()
            jm_pairs.append(MeetingJudgeNode(f"mj_{i}", meeting, judges[i % 3]))
        
        # 30 pairs requiring security
        for i in range(40, 70):
            case = Case(case_id=i, characteristics={Attribute.CIVIL})
            case.room_requirements = {Attribute.SECURITY}
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=30,
                duration_of_stay=0,
                judge=judges[i % 3],
                room=None,
                case=case
            )
            judges[i % 3].room_requirements = set()
            jm_pairs.append(MeetingJudgeNode(f"mj_{i}", meeting, judges[i % 3]))
        
        # 30 pairs requiring virtual
        for i in range(70, 100):
            case = Case(case_id=i, characteristics={Attribute.TVANG})
            case.room_requirements = {Attribute.VIRTUAL}
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=30,
                duration_of_stay=0,
                judge=judges[i % 3],
                room=None,
                case=case
            )
            judges[i % 3].room_requirements = set()
            jm_pairs.append(MeetingJudgeNode(f"mj_{i}", meeting, judges[i % 3]))
        
        # Calculate room capacities
        capacities = calculate_all_room_capacities(jm_pairs, rooms)
        
        # Verify total capacity equals total pairs
        total_capacity = sum(capacities.values())
        total_pairs = len(jm_pairs)
        
        self.assertEqual(total_capacity, total_pairs,
                        f"Room capacity mismatch: assigned {total_capacity}, but have {total_pairs} pairs")
        
        # Verify each room has non-negative capacity
        for room_id, capacity in capacities.items():
            self.assertGreaterEqual(capacity, 0, 
                                   f"Room {room_id} has negative capacity: {capacity}")
    
    def test_room_capacity_with_competing_rooms(self):
        """
        Test capacity calculation when multiple rooms can handle the same requirements.
        This tests the weight distribution logic.
        """
        # Two identical rooms that can handle everything
        rooms = [
            Room(room_id=1, characteristics={Attribute.SECURITY, Attribute.VIRTUAL}),
            Room(room_id=2, characteristics={Attribute.SECURITY, Attribute.VIRTUAL})
        ]
        
        judges = [Judge(judge_id=1, characteristics={Attribute.STRAFFE})]
        
        # Create 10 pairs with security requirement
        jm_pairs = []
        for i in range(10):
            case = Case(case_id=i, characteristics={Attribute.STRAFFE})
            case.room_requirements = {Attribute.SECURITY}
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=30,
                duration_of_stay=0,
                judge=judges[0],
                room=None,
                case=case
            )
            judges[0].room_requirements = set()
            jm_pairs.append(MeetingJudgeNode(f"mj_{i}", meeting, judges[0]))
        
        capacities = calculate_all_room_capacities(jm_pairs, rooms)
        
        # Both rooms should get equal capacity (5 each)
        self.assertEqual(capacities[1], 5, "Room 1 should get 5 pairs")
        self.assertEqual(capacities[2], 5, "Room 2 should get 5 pairs")
        self.assertEqual(sum(capacities.values()), 10, "Total capacity should be 10")
    
    def test_room_capacity_with_exclusive_requirements(self):
        """
        Test capacity calculation when rooms have exclusive capabilities.
        """
        rooms = [
            Room(room_id=1, characteristics={Attribute.SECURITY}),  # Only security
            Room(room_id=2, characteristics={Attribute.VIRTUAL}),   # Only virtual
            Room(room_id=3, characteristics=set())  # Generic
        ]
        
        judges = [Judge(judge_id=1, characteristics={Attribute.STRAFFE})]
        
        jm_pairs = []
        
        # 10 pairs requiring security (can only go to room 1)
        for i in range(10):
            case = Case(case_id=i, characteristics={Attribute.STRAFFE})
            case.room_requirements = {Attribute.SECURITY}
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=30,
                duration_of_stay=0,
                judge=judges[0],
                room=None,
                case=case
            )
            judges[0].room_requirements = set()
            jm_pairs.append(MeetingJudgeNode(f"mj_{i}", meeting, judges[0]))
        
        # 10 pairs requiring virtual (can only go to room 2)
        for i in range(10, 20):
            case = Case(case_id=i, characteristics={Attribute.STRAFFE})
            case.room_requirements = {Attribute.VIRTUAL}
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=30,
                duration_of_stay=0,
                judge=judges[0],
                room=None,
                case=case
            )
            judges[0].room_requirements = set()
            jm_pairs.append(MeetingJudgeNode(f"mj_{i}", meeting, judges[0]))
        
        # 10 pairs with no requirements (can go to room 3)
        for i in range(20, 30):
            case = Case(case_id=i, characteristics={Attribute.STRAFFE})
            case.room_requirements = set()
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=30,
                duration_of_stay=0,
                judge=judges[0],
                room=None,
                case=case
            )
            judges[0].room_requirements = set()
            jm_pairs.append(MeetingJudgeNode(f"mj_{i}", meeting, judges[0]))
        
        capacities = calculate_all_room_capacities(jm_pairs, rooms)
        
        # Debug output
        print(f"\nRoom capacities:")
        for room_id, capacity in capacities.items():
            print(f"  Room {room_id}: {capacity}")
        print(f"Total: {sum(capacities.values())}")
        
        # Verify correct distribution
        # Room 1 gets all 10 security pairs + 1/3 of generic pairs
        # Room 2 gets all 10 virtual pairs + 1/3 of generic pairs  
        # Room 3 gets only 1/3 of generic pairs
        # Due to rounding, the distribution will be approximately 13, 13, 4
        self.assertIn(capacities[1], [13, 14], f"Room 1 should get ~13 pairs, got {capacities[1]}")
        self.assertIn(capacities[2], [13, 14], f"Room 2 should get ~13 pairs, got {capacities[2]}")
        self.assertIn(capacities[3], [3, 4], f"Room 3 should get ~3-4 pairs, got {capacities[3]}")
        self.assertEqual(sum(capacities.values()), 30, "Total capacity should be 30")
    
    def test_fractional_distribution_accuracy(self):
        """
        Test that fractional distribution doesn't create overcounting.
        This is likely where the bug is - in the fractional remainder calculation.
        """
        # 3 identical rooms
        rooms = [
            Room(room_id=1, characteristics=set()),
            Room(room_id=2, characteristics=set()),
            Room(room_id=3, characteristics=set())
        ]
        
        judges = [Judge(judge_id=1, characteristics={Attribute.STRAFFE})]
        
        # Create 10 identical pairs (should distribute 3, 3, 4)
        jm_pairs = []
        for i in range(10):
            case = Case(case_id=i, characteristics={Attribute.STRAFFE})
            case.room_requirements = set()
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=30,
                duration_of_stay=0,
                judge=judges[0],
                room=None,
                case=case
            )
            judges[0].room_requirements = set()
            jm_pairs.append(MeetingJudgeNode(f"mj_{i}", meeting, judges[0]))
        
        capacities = calculate_all_room_capacities(jm_pairs, rooms)
        
        # Total should be exactly 10
        total = sum(capacities.values())
        self.assertEqual(total, 10, f"Total capacity {total} != 10 pairs")
        
        # Each room should get 3 or 4
        for room_id, capacity in capacities.items():
            self.assertIn(capacity, [3, 4], 
                         f"Room {room_id} has unexpected capacity {capacity}")


    def test_debug_capacity_calculation_bug(self):
        """
        Debug test to understand why rooms get wrong capacities.
        This will help identify the root cause of the "Assigned: 105, Total: 100" warning.
        """
        rooms = [
            Room(room_id=1, characteristics={Attribute.SECURITY}),  # Only security
            Room(room_id=2, characteristics={Attribute.VIRTUAL}),   # Only virtual
            Room(room_id=3, characteristics=set())  # Generic - no characteristics
        ]
        
        judges = [Judge(judge_id=1, characteristics={Attribute.STRAFFE})]
        
        jm_pairs = []
        
        # 10 pairs requiring security
        for i in range(10):
            case = Case(case_id=i, characteristics={Attribute.STRAFFE})
            case.room_requirements = {Attribute.SECURITY}
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=30,
                duration_of_stay=0,
                judge=judges[0],
                room=None,
                case=case
            )
            judges[0].room_requirements = set()
            jm_pairs.append(MeetingJudgeNode(f"mj_{i}", meeting, judges[0]))
        
        # 10 pairs requiring virtual
        for i in range(10, 20):
            case = Case(case_id=i, characteristics={Attribute.STRAFFE})
            case.room_requirements = {Attribute.VIRTUAL}
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=30,
                duration_of_stay=0,
                judge=judges[0],
                room=None,
                case=case
            )
            judges[0].room_requirements = set()
            jm_pairs.append(MeetingJudgeNode(f"mj_{i}", meeting, judges[0]))
        
        # 10 pairs with no requirements
        for i in range(20, 30):
            case = Case(case_id=i, characteristics={Attribute.STRAFFE})
            case.room_requirements = set()
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=30,
                duration_of_stay=0,
                judge=judges[0],
                room=None,
                case=case
            )
            judges[0].room_requirements = set()
            jm_pairs.append(MeetingJudgeNode(f"mj_{i}", meeting, judges[0]))
        
        # First check compatibility assumptions
        print("\n=== Compatibility Check ===")
        from src.base_model.compatibility_checks import case_room_compatible, judge_room_compatible
        
        # Test samples
        security_pair = jm_pairs[0]  # Requires security
        virtual_pair = jm_pairs[10]  # Requires virtual  
        generic_pair = jm_pairs[20]  # No requirements
        
        for room in rooms:
            print(f"\nRoom {room.room_id} (chars: {room.characteristics}):")
            
            # Security pair
            sec_case_compat = case_room_compatible(security_pair.get_meeting().case, room)
            sec_judge_compat = judge_room_compatible(security_pair.get_judge(), room)
            print(f"  Security pair: case_compat={sec_case_compat}, judge_compat={sec_judge_compat}")
            
            # Virtual pair
            virt_case_compat = case_room_compatible(virtual_pair.get_meeting().case, room)
            virt_judge_compat = judge_room_compatible(virtual_pair.get_judge(), room)
            print(f"  Virtual pair: case_compat={virt_case_compat}, judge_compat={virt_judge_compat}")
            
            # Generic pair
            gen_case_compat = case_room_compatible(generic_pair.get_meeting().case, room)
            gen_judge_compat = judge_room_compatible(generic_pair.get_judge(), room)
            print(f"  Generic pair: case_compat={gen_case_compat}, judge_compat={gen_judge_compat}")
        
        # Debug the calculation
        print("\n=== Debug: Room Capacity Calculation ===")
        capacities = self._debug_capacity_calculation(jm_pairs, rooms)
        
        print(f"\nFinal capacities:")
        for room_id, capacity in capacities.items():
            print(f"  Room {room_id}: {capacity}")
        print(f"Total: {sum(capacities.values())}")
        
        # Check if we can reproduce the overcounting issue
        total = sum(capacities.values())
        self.assertEqual(total, 30, f"Total capacity {total} != 30 pairs")
    
    def _debug_capacity_calculation(self, jm_pairs, rooms):
        """Debug version of calculate_all_room_capacities to trace the bug."""
        from src.base_model.compatibility_checks import case_room_compatible, judge_room_compatible
        
        # Group pairs by requirements
        requirement_groups = {}
        for jm_pair in jm_pairs:
            combined_req = frozenset(
                list(jm_pair.meeting.case.room_requirements) + 
                list(jm_pair.judge.room_requirements)
            )
            if combined_req not in requirement_groups:
                requirement_groups[combined_req] = []
            requirement_groups[combined_req].append(jm_pair)
        
        print(f"\nRequirement groups:")
        for req, pairs in requirement_groups.items():
            print(f"  {set(req)}: {len(pairs)} pairs")
        
        group_counts = {req: len(pairs_list) for req, pairs_list in requirement_groups.items()}
        
        # Calculate weights
        room_weights = {}
        print(f"\nWeight calculation:")
        for room in rooms:
            room_weights[room.room_id] = {}
            print(f"\nRoom {room.room_id}:")
            for req_group, pairs_in_group in requirement_groups.items():
                if pairs_in_group:
                    sample_pair = pairs_in_group[0]
                    compatible = (case_room_compatible(sample_pair.get_meeting().case, room) and 
                                judge_room_compatible(sample_pair.get_judge(), room))
                    
                    competing_rooms = sum(1 for r in rooms if 
                                        case_room_compatible(sample_pair.get_meeting().case, r) and 
                                        judge_room_compatible(sample_pair.get_judge(), r))
                    
                    weight = 1.0 / max(1, competing_rooms) if compatible else 0
                    room_weights[room.room_id][req_group] = weight
                    print(f"  {set(req_group)}: compatible={compatible}, competing={competing_rooms}, weight={weight}")
        
        # Calculate float capacities
        float_capacities = {}
        print(f"\nFloat capacities:")
        for room in rooms:
            capacity = 0.0
            for req_group, count in group_counts.items():
                weight = room_weights[room.room_id][req_group]
                capacity += weight * count
            float_capacities[room.room_id] = capacity
            print(f"  Room {room.room_id}: {capacity}")
        
        # Convert to integers
        int_capacities = {room_id: int(cap) for room_id, cap in float_capacities.items()}
        print(f"\nInteger capacities: {int_capacities}")
        print(f"Total integer: {sum(int_capacities.values())}")
        
        # Calculate fractional remainders
        group_fractional_pairs = {}
        print(f"\nFractional remainders by group:")
        for req_group, count in group_counts.items():
            integer_assigned = sum(
                int(room_weights[r.room_id][req_group] * count)
                for r in rooms
            )
            fractional_remaining = count - integer_assigned
            print(f"  {set(req_group)}: count={count}, assigned={integer_assigned}, remaining={fractional_remaining}")
            if fractional_remaining > 0:
                group_fractional_pairs[req_group] = fractional_remaining
        
        # Distribute remainders
        print(f"\nDistributing remainders:")
        for req_group, remaining_count in group_fractional_pairs.items():
            print(f"  Distributing {remaining_count} for {set(req_group)}")
            
            eligible_rooms = []
            for room in rooms:
                if room_weights[room.room_id][req_group] > 0:
                    fractional_part = float_capacities[room.room_id] - int_capacities[room.room_id]
                    if fractional_part > 0:
                        eligible_rooms.append({
                            'room_id': room.room_id,
                            'current_capacity': int_capacities[room.room_id],
                            'remainder': fractional_part
                        })
            
            eligible_rooms.sort(key=lambda x: (x['current_capacity'], -x['remainder']))
            
            assigned = 0
            for eligible_room in eligible_rooms:
                if assigned < remaining_count:
                    int_capacities[eligible_room['room_id']] += 1
                    assigned += 1
                    print(f"    Assigned 1 to room {eligible_room['room_id']}")
        
        return int_capacities


    def test_reproduce_overcounting_bug(self):
        """
        Try to reproduce the bug where total assigned exceeds total pairs.
        The warning: "Assigned: 105, Total: 100" suggests overcounting.
        """
        # Create a scenario with many rooms and complex requirements
        rooms = []
        for i in range(1, 11):  # 10 rooms
            if i <= 3:
                rooms.append(Room(room_id=i, characteristics={Attribute.SECURITY}))
            elif i <= 6:
                rooms.append(Room(room_id=i, characteristics={Attribute.VIRTUAL}))
            elif i <= 8:
                rooms.append(Room(room_id=i, characteristics={Attribute.SECURITY, Attribute.VIRTUAL}))
            else:
                rooms.append(Room(room_id=i, characteristics=set()))
        
        judges = [
            Judge(judge_id=1, characteristics={Attribute.STRAFFE}),
            Judge(judge_id=2, characteristics={Attribute.CIVIL}),
            Judge(judge_id=3, characteristics={Attribute.TVANG}),
            Judge(judge_id=4, characteristics={Attribute.STRAFFE, Attribute.CIVIL})
        ]
        
        # Create 100 pairs with mixed requirements
        jm_pairs = []
        requirements_distribution = [
            ({Attribute.SECURITY}, 25),
            ({Attribute.VIRTUAL}, 25),
            ({Attribute.SECURITY, Attribute.VIRTUAL}, 15),
            (set(), 35)
        ]
        
        pair_id = 0
        for req_set, count in requirements_distribution:
            for _ in range(count):
                case = Case(case_id=pair_id, characteristics={Attribute.STRAFFE})
                case.room_requirements = req_set
                meeting = Meeting(
                    meeting_id=pair_id,
                    meeting_duration=30,
                    duration_of_stay=0,
                    judge=judges[pair_id % len(judges)],
                    room=None,
                    case=case
                )
                judges[pair_id % len(judges)].room_requirements = set()
                jm_pairs.append(MeetingJudgeNode(f"mj_{pair_id}", meeting, judges[pair_id % len(judges)]))
                pair_id += 1
        
        print(f"\nTest setup: {len(jm_pairs)} pairs, {len(rooms)} rooms")
        
        # Calculate capacities with detailed debugging
        print("\n=== Detailed Debug ===")
        capacities = self._debug_capacity_calculation_detailed(jm_pairs, rooms)
        
        total_capacity = sum(capacities.values())
        print(f"\nResult: Total capacity = {total_capacity}, Expected = {len(jm_pairs)}")
        
        # The bug would show total_capacity > len(jm_pairs)
        self.assertEqual(total_capacity, len(jm_pairs),
                        f"Capacity mismatch: assigned {total_capacity}, but have {len(jm_pairs)} pairs")


    def _debug_capacity_calculation_detailed(self, jm_pairs, rooms):
        """Detailed debug of the capacity calculation to find overcounting."""
        from src.base_model.compatibility_checks import case_room_compatible, judge_room_compatible
        
        # Use the actual function but capture intermediate results
        from src.base_model.capacity_calculator import calculate_all_room_capacities
        
        # First run the actual function to see the warning
        print("\nRunning actual capacity calculation...")
        actual_result = calculate_all_room_capacities(jm_pairs, rooms)
        print(f"Actual result sum: {sum(actual_result.values())}")
        
        # Now trace through to find where overcounting happens
        requirement_groups = {}
        for jm_pair in jm_pairs:
            combined_req = frozenset(
                list(jm_pair.meeting.case.room_requirements) + 
                list(jm_pair.judge.room_requirements)
            )
            if combined_req not in requirement_groups:
                requirement_groups[combined_req] = []
            requirement_groups[combined_req].append(jm_pair)
        
        group_counts = {req: len(pairs_list) for req, pairs_list in requirement_groups.items()}
        print(f"\nRequirement groups summary:")
        total_in_groups = 0
        for req, count in group_counts.items():
            print(f"  {set(req) if req else 'No requirements'}: {count} pairs")
            total_in_groups += count
        print(f"  Total in groups: {total_in_groups}")
        
        return actual_result


    def test_simple_overcounting_case(self):
        """
        Simple test case to understand overcounting.
        """
        # 2 rooms that can handle everything
        rooms = [
            Room(room_id=1, characteristics={Attribute.SECURITY, Attribute.VIRTUAL}),
            Room(room_id=2, characteristics={Attribute.SECURITY, Attribute.VIRTUAL})
        ]
        
        judges = [Judge(judge_id=1, characteristics={Attribute.STRAFFE})]
        
        # Create 7 pairs: 3 security, 3 virtual, 1 both
        jm_pairs = []
        
        # 3 security
        for i in range(3):
            case = Case(case_id=i, characteristics={Attribute.STRAFFE})
            case.room_requirements = {Attribute.SECURITY}
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=30,
                duration_of_stay=0,
                judge=judges[0],
                room=None,
                case=case
            )
            judges[0].room_requirements = set()
            jm_pairs.append(MeetingJudgeNode(f"mj_{i}", meeting, judges[0]))
        
        # 3 virtual
        for i in range(3, 6):
            case = Case(case_id=i, characteristics={Attribute.STRAFFE})
            case.room_requirements = {Attribute.VIRTUAL}
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=30,
                duration_of_stay=0,
                judge=judges[0],
                room=None,
                case=case
            )
            judges[0].room_requirements = set()
            jm_pairs.append(MeetingJudgeNode(f"mj_{i}", meeting, judges[0]))
        
        # 1 both
        case = Case(case_id=6, characteristics={Attribute.STRAFFE})
        case.room_requirements = {Attribute.SECURITY, Attribute.VIRTUAL}
        meeting = Meeting(
            meeting_id=6,
            meeting_duration=30,
            duration_of_stay=0,
            judge=judges[0],
            room=None,
            case=case
        )
        judges[0].room_requirements = set()
        jm_pairs.append(MeetingJudgeNode(f"mj_6", meeting, judges[0]))
        
        print(f"\nSimple test: {len(jm_pairs)} pairs, {len(rooms)} rooms")
        print("Expected: Each room gets 3.5 pairs")
        
        capacities = calculate_all_room_capacities(jm_pairs, rooms)
        
        print(f"\nResult:")
        for room_id, cap in capacities.items():
            print(f"  Room {room_id}: {cap}")
        print(f"  Total: {sum(capacities.values())}")
        
        self.assertEqual(sum(capacities.values()), 7, "Should assign exactly 7 pairs")


if __name__ == '__main__':
    unittest.main()