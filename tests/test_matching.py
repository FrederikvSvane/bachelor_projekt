import unittest
from src.graph_construction.matching import *
from src.schedule import *
from src.graph_construction.graph import *
from src.model import *
import random

class TestMatching(unittest.TestCase):
    
    def test_matching_cases_to_judges(self):
        """
        Test that cases are correctly matched to judges.
        
        Scenario:
        - 3 judges with different skills
        - 6 cases with different durations
        
        Expected outcome:
        - All judges have 2 cases scheduled
        """
        # Create judges
        judges = [
            Judge(judge_id=1, characteristics={Attribute.STRAFFE}, case_requirements={Attribute.STRAFFE}),
            Judge(judge_id=2, characteristics={Attribute.TVANG}, case_requirements={Attribute.TVANG}),
            Judge(judge_id=3, characteristics={Attribute.CIVIL}, case_requirements={Attribute.CIVIL})
        ]
        
        # Create cases
        cases = [
            Case(case_id=1, case_duration=60, characteristics={Attribute.STRAFFE}, judge_requirements={Attribute.STRAFFE}),
            Case(case_id=2, case_duration=120, characteristics={Attribute.STRAFFE}, judge_requirements={Attribute.STRAFFE}),
            Case(case_id=3, case_duration=180, characteristics={Attribute.TVANG}, judge_requirements={Attribute.TVANG}),
            Case(case_id=4, case_duration=240, characteristics={Attribute.TVANG}, judge_requirements={Attribute.TVANG}),
            Case(case_id=5, case_duration=300, characteristics={Attribute.CIVIL}, judge_requirements={Attribute.CIVIL}),
            Case(case_id=6, case_duration=360, characteristics={Attribute.CIVIL}, judge_requirements={Attribute.CIVIL})
        ]
        
        graph = DirectedGraph()
        graph.initialize_case_to_judge_graph(cases, judges)
        
        # Assign cases to judges
        judge_case_assignments: List[CaseJudgeNode] = assign_cases_to_judges(graph)
        cases_per_judge = {judge.judge_id: 0 for judge in judges}
        for node in judge_case_assignments:
            cases_per_judge[node.get_judge().judge_id] += 1
        
        self.assertEqual(cases_per_judge[1], 2)
        self.assertEqual(cases_per_judge[2], 2)
        self.assertEqual(cases_per_judge[3], 2)
        
    def test_judge_with_zero_cases(self):
        """
        Test the edge case where a judge is assigned 0 cases.
        
        Scenario:
        - 3 judges with specific skills
        - 1 judge has skills that don't match any cases
        - Cases only require skills that the other 2 judges have
        
        Expected outcome:
        - 2 judges have cases assigned
        - 1 judge has zero cases assigned
        """
        # Create judges
        judges = [
            Judge(judge_id=1, characteristics={Attribute.STRAFFE}, case_requirements={Attribute.STRAFFE}),
            Judge(judge_id=2, characteristics={Attribute.TVANG}, case_requirements={Attribute.TVANG}),
            Judge(judge_id=3, characteristics={Attribute.CIVIL}, case_requirements={})  # No cases need this skill
        ]
        
        # Create cases - none require CIVIL
        cases = [
            Case(case_id=1, case_duration=60, characteristics={Attribute.STRAFFE}, judge_requirements={Attribute.STRAFFE}),
            Case(case_id=2, case_duration=120, characteristics={Attribute.STRAFFE}, judge_requirements={Attribute.STRAFFE}),
            Case(case_id=3, case_duration=180, characteristics={Attribute.TVANG}, judge_requirements={Attribute.TVANG}),
            Case(case_id=4, case_duration=240, characteristics={Attribute.TVANG}, judge_requirements={Attribute.TVANG}),
        ]
        
        graph = DirectedGraph()
        graph.initialize_case_to_judge_graph(cases, judges)
        
        # Assign cases to judges
        judge_case_assignments: List[CaseJudgeNode] = assign_cases_to_judges(graph)
        cases_per_judge = {judge.judge_id: 0 for judge in judges}
        for node in judge_case_assignments:
            cases_per_judge[node.get_judge().judge_id] += 1
        
        # Verify assignments
        self.assertEqual(len(judge_case_assignments), 4, "All cases should be assigned")
        self.assertEqual(cases_per_judge[1], 2, "Judge 1 should have 2 STRAFFE cases")
        self.assertEqual(cases_per_judge[2], 2, "Judge 2 should have 2 TVANG cases")
        self.assertEqual(cases_per_judge[3], 0, "Judge 3 should have 0 cases")
        
        

        
        