import unittest

from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.attribute_enum import Attribute
from src.base_model.meeting import Meeting
from src.base_model.capacity_calculator import calculate_all_judge_capacities

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
                characteristics = {Attribute.CIVIL},
                meetings=[]
            )
            cases.append(case)
            civil_cases.append(case)
            
        # Create 50 criminal cases
        criminal_cases = []
        for i in range(51, 101):
            case = Case(
                case_id=i,
                characteristics= {Attribute.STRAFFE},
                meetings=[]
            )
            cases.append(case)
            criminal_cases.append(case)
        
        meetings = []
        for case in cases:
            case.meetings = [Meeting(case.case_id, 120, 0, None, None, case)]
            meetings.extend(case.meetings)
        
        # Create judges with different skill sets
        judges = [
            # Civil-only judges
            Judge(judge_id=1, characteristics={Attribute.CIVIL}),
            Judge(judge_id=2, characteristics={Attribute.CIVIL}),
            
            # Criminal-only judges
            Judge(judge_id=3, characteristics={Attribute.STRAFFE}),
            Judge(judge_id=4, characteristics={Attribute.STRAFFE}),
            
            # Versatile judge (both civil and criminal)
            Judge(judge_id=5, characteristics={Attribute.STRAFFE, Attribute.CIVIL})
        ]
        
        # Calculate capacity for each judge
        capacities = calculate_all_judge_capacities(meetings, judges)
        
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
            Case(case_id=1,  characteristics={Attribute.CIVIL}, judge_requirements={Attribute.CIVIL}),
            Case(case_id=2,  characteristics={Attribute.CIVIL}, judge_requirements={Attribute.CIVIL}),
            Case(case_id=3,  characteristics={Attribute.CIVIL}, judge_requirements={Attribute.CIVIL}),
            Case(case_id=4,  characteristics={Attribute.CIVIL}, judge_requirements={Attribute.CIVIL}),
            Case(case_id=5,  characteristics={Attribute.CIVIL}, judge_requirements={Attribute.CIVIL}),
            Case(case_id=6,  characteristics={Attribute.STRAFFE}, judge_requirements={Attribute.STRAFFE}),
            Case(case_id=7,  characteristics={Attribute.STRAFFE}, judge_requirements={Attribute.STRAFFE}),
            Case(case_id=8,  characteristics={Attribute.STRAFFE}, judge_requirements={Attribute.STRAFFE}),
            Case(case_id=9,  characteristics={Attribute.STRAFFE}, judge_requirements={Attribute.STRAFFE}),
            Case(case_id=10, characteristics={Attribute.STRAFFE}, judge_requirements={Attribute.STRAFFE}),
        ]
        judges = [
            # This judge is incompatible with all cases (TVANG only)
            Judge(judge_id=1, characteristics={Attribute.TVANG}, case_requirements=set()),
            # This judge can only handle CIVIL cases
            Judge(judge_id=2, characteristics={Attribute.CIVIL, Attribute.TVANG}, case_requirements=set()),
            # These judges can handle both CIVIL and STRAFFE cases
            Judge(judge_id=3, characteristics={Attribute.CIVIL, Attribute.STRAFFE, Attribute.TVANG}, case_requirements=set()),
            Judge(judge_id=4, characteristics={Attribute.CIVIL, Attribute.STRAFFE, Attribute.TVANG}, case_requirements=set()),
            Judge(judge_id=5, characteristics={Attribute.CIVIL, Attribute.STRAFFE, Attribute.TVANG}, case_requirements=set()),
        ]
        
        meetings = []
        for case in cases:
            case.meetings = [Meeting(case.case_id, 120, 0, None, None, case)]
            meetings.extend(case.meetings)
        
        capacities = calculate_all_judge_capacities(meetings, judges)
        
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