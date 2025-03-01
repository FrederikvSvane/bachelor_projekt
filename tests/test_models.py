# tests/test_models.py
import unittest
from src.models import Judge, Meeting, Sagstype, calculate_judge_capacity

class TestJudgeCapacity(unittest.TestCase):
    def test_case_distribution_with_mixed_skills(self):
        """
        Test that cases are distributed appropriately based on judge skills.
        
        Scenario:
        - 2 judges who can only handle civil cases (judge_ids 1,2)
        - 2 judges who can only handle criminal cases (judge_ids 3,4)
        - 1 judge who can handle both types (judge_id 5)
        - 50 civil cases and 50 criminal cases
        
        Expected outcome:
        - Each civil-only judge gets 20 civil cases
        - Each criminal-only judge gets 20 criminal cases
        - The versatile judge gets 10 civil + 10 criminal cases (20 total)
        """
        # Create meetings: 50 civil and 50 criminal
        meetings = []
        
        # Create 50 civil meetings
        civil_meetings = []
        for i in range(1, 51):
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=60,
                meeting_sagstype=Sagstype.CIVILE,
                meeting_virtual=False
            )
            meetings.append(meeting)
            civil_meetings.append(meeting)
            
        # Create 50 criminal meetings
        criminal_meetings = []
        for i in range(51, 101):
            meeting = Meeting(
                meeting_id=i,
                meeting_duration=60,
                meeting_sagstype=Sagstype.STRAFFE,
                meeting_virtual=False
            )
            meetings.append(meeting)
            criminal_meetings.append(meeting)
        
        # Create judges with different skill sets
        judges = [
            # Civil-only judges
            Judge(judge_id=1, judge_skills=[Sagstype.CIVILE], judge_virtual=False),
            Judge(judge_id=2, judge_skills=[Sagstype.CIVILE], judge_virtual=False),
            
            # Criminal-only judges
            Judge(judge_id=3, judge_skills=[Sagstype.STRAFFE], judge_virtual=False),
            Judge(judge_id=4, judge_skills=[Sagstype.STRAFFE], judge_virtual=False),
            
            # Versatile judge (both civil and criminal)
            Judge(judge_id=5, judge_skills=[Sagstype.CIVILE, Sagstype.STRAFFE], judge_virtual=False)
        ]
        
        # Calculate capacity for each judge
        capacities = {}
        for judge in judges:
            capacities[judge.judge_id] = calculate_judge_capacity(meetings, judges, judge.judge_id)
        
        # Test total capacities
        self.assertEqual(capacities[1], 20, "First civil-only judge should get 20 cases")
        self.assertEqual(capacities[2], 20, "Second civil-only judge should get 20 cases")
        self.assertEqual(capacities[3], 20, "First criminal-only judge should get 20 cases")
        self.assertEqual(capacities[4], 20, "Second criminal-only judge should get 20 cases")
        self.assertEqual(capacities[5], 20, "Versatile judge should get 20 cases total")
        
        # Now test the distribution of cases for the versatile judge
        # We need to create a mock assignment of cases to judges based on the capacities
        
        # For simplicity, assume that civil-only judges get civil cases first
        # and criminal-only judges get criminal cases first
        remaining_civil = civil_meetings.copy()
        remaining_criminal = criminal_meetings.copy()
        
        # Assign to civil-only judges
        civil_only_cases = remaining_civil[:capacities[1] + capacities[2]]
        remaining_civil = remaining_civil[capacities[1] + capacities[2]:]
        
        # Assign to criminal-only judges
        criminal_only_cases = remaining_criminal[:capacities[3] + capacities[4]]
        remaining_criminal = remaining_criminal[capacities[3] + capacities[4]:]
        
        # The versatile judge should get the remaining cases
        versatile_civil_cases = remaining_civil
        versatile_criminal_cases = remaining_criminal
        
        # Check that the versatile judge gets exactly 10 of each type
        self.assertEqual(len(versatile_civil_cases), 10, 
                        f"Versatile judge should get exactly 10 civil cases but got {len(versatile_civil_cases)}")
        self.assertEqual(len(versatile_criminal_cases), 10, 
                        f"Versatile judge should get exactly 10 criminal cases but got {len(versatile_criminal_cases)}")
        
        # Verify that total case distribution matches expectations
        self.assertEqual(len(civil_only_cases) + len(versatile_civil_cases), 50, 
                        "Total civil cases distributed should be 50")
        self.assertEqual(len(criminal_only_cases) + len(versatile_criminal_cases), 50, 
                        "Total criminal cases distributed should be 50")
        
        # Verify total capacity matches total meetings
        total_capacity = sum(capacities.values())
        self.assertEqual(total_capacity, len(meetings), 
                         f"Total capacity ({total_capacity}) should match total meetings ({len(meetings)})")

if __name__ == "__main__":
    unittest.main()