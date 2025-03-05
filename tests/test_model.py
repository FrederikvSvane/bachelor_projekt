# tests/test_models.py
import unittest
from src.model import Judge, Case, Attribute, calculate_all_judge_capacities

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
        # Create cases: 50 civil and 50 criminal
        cases = []
        
        # Create 50 civil cases
        civil_cases = []
        for i in range(1, 51):
            case = Case(
                case_id=i,
                case_duration=60,
                characteristics = {Attribute.CIVIL},
                case_virtual=False
            )
            cases.append(case)
            civil_cases.append(case)
            
        # Create 50 criminal cases
        criminal_cases = []
        for i in range(51, 101):
            case = Case(
                case_id=i,
                case_duration=60,
                characteristics= {Attribute.STRAFFE},
                case_virtual=False
            )
            cases.append(case)
            criminal_cases.append(case)
        
        # Create judges with different skill sets
        judges = [
            # Civil-only judges
            Judge(judge_id=1, characteristics={Attribute.CIVIL}, judge_virtual=False),
            Judge(judge_id=2, characteristics={Attribute.CIVIL}, judge_virtual=False),
            
            # Criminal-only judges
            Judge(judge_id=3, characteristics={Attribute.STRAFFE}, judge_virtual=False),
            Judge(judge_id=4, characteristics={Attribute.STRAFFE}, judge_virtual=False),
            
            # Versatile judge (both civil and criminal)
            Judge(judge_id=5, characteristics={Attribute.STRAFFE, Attribute.CIVIL}, judge_virtual=False)
        ]
        
        # Calculate capacity for each judge
        capacities = calculate_all_judge_capacities(cases, judges)
        
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
        remaining_civil = civil_cases.copy()
        remaining_criminal = criminal_cases.copy()
        
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
        
        # Verify total capacity matches total cases
        total_capacity = sum(capacities.values())
        self.assertEqual(total_capacity, len(cases), 
                         f"Total capacity ({total_capacity}) should match total cases ({len(cases)})")
    
    def test_incompatible_judge_gets_zero_capacity(self):
        """
        Test that a judge with unapplicable skill gets 0 cases assigned
        """
        cases = [
            Case(1, 1, Attribute.CIVIL, case_virtual=False),
            Case(2, 1, Attribute.CIVIL, case_virtual=False),
            Case(3, 1, Attribute.CIVIL, case_virtual=False),
            Case(4, 1, Attribute.CIVIL, case_virtual=False),
            Case(5, 1, Attribute.CIVIL, case_virtual=False),
            Case(6, 1, Attribute.STRAFFE, case_virtual=False),
            Case(7, 1, Attribute.STRAFFE, case_virtual=False),
            Case(8, 1, Attribute.STRAFFE, case_virtual=False),
            Case(9, 1, Attribute.STRAFFE, case_virtual=False),
            Case(10, 1, Attribute.STRAFFE, case_virtual=False),
        ]
        judges = [
            Judge(1, [Attribute.TVANG], False),
            Judge(2, [Attribute.CIVIL, Attribute.TVANG], False),
            Judge(3, [Attribute.CIVIL, Attribute.STRAFFE, Attribute.TVANG], judge_virtual=False),
            Judge(4, [Attribute.CIVIL, Attribute.STRAFFE, Attribute.TVANG], judge_virtual=False),
            Judge(5, [Attribute.CIVIL, Attribute.STRAFFE, Attribute.TVANG], judge_virtual=False),
        ]
        
        capacities = calculate_all_judge_capacities(cases, judges)
        
        print(capacities)
        
        # Calculated by hand
        self.assertEqual(capacities[1], 0,
                         f"Judge 1 should get 0 cases but got {capacities[1]}")    
        self.assertEqual(capacities[2], 0.1*10,
                         f"Judge 2 should get 1 cases but got {capacities[2]}")    
        self.assertEqual(capacities[3], 3,
                         f"Judge 3 should get 3 cases but got {capacities[3]}")    
        self.assertEqual(capacities[4], 3,
                         f"Judge 4 should get 3 cases but got {capacities[4]}")    
        self.assertEqual(capacities[5], 3,
                         f"Judge 5 should get 3 cases but got {capacities[5]}")    
        

if __name__ == "__main__":
    unittest.main()