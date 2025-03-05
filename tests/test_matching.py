import unittest
from src.models import Judge, Meeting, Sagstype, calculate_judge_capacity, calculate_all_judge_capacities
from src.matching import *
from src.schedule import *
from src.graph import *
from src.models import *
import random

class TestMatching(unittest.TestCase):
    
    def test_matching_meetings_to_judges(self):
        """
        Test that meetings are correctly matched to judges.
        
        Scenario:
        - 3 judges with different skills
        - 6 meetings with different durations
        
        Expected outcome:
        - All judges have 2 meetings scheduled
        """
        # Create judges
        judges = [
            Judge(judge_id=1, judge_skills=[Sagstype.STRAFFE], judge_virtual=False),
            Judge(judge_id=2, judge_skills=[Sagstype.TVANG], judge_virtual=False),
            Judge(judge_id=3, judge_skills=[Sagstype.CIVIL], judge_virtual=False)
        ]
        
        # Create meetings
        meetings = [
            Meeting(meeting_id=1, meeting_duration=60, meeting_sagstype=Sagstype.CIVIL, meeting_virtual=False),
            Meeting(meeting_id=2, meeting_duration=120, meeting_sagstype=Sagstype.CIVIL, meeting_virtual=False),
            Meeting(meeting_id=3, meeting_duration=180, meeting_sagstype=Sagstype.STRAFFE, meeting_virtual=False),
            Meeting(meeting_id=4, meeting_duration=240, meeting_sagstype=Sagstype.STRAFFE, meeting_virtual=False),
            Meeting(meeting_id=5, meeting_duration=300, meeting_sagstype=Sagstype.TVANG, meeting_virtual=False),
            Meeting(meeting_id=6, meeting_duration=360, meeting_sagstype=Sagstype.TVANG, meeting_virtual=False)
        ]
        
        graph = DirectedGraph()
        graph.initialize_judge_case_graph(meetings, judges)
        
        # Assign meetings to judges
        judge_meeting_assignments: List[MeetingJudgeNode] = assign_judges_to_meetings(graph)
        meetings_per_judge = {judge.judge_id: 0 for judge in judges}
        for node in judge_meeting_assignments:
            meetings_per_judge[node.get_judge().judge_id] += 1
        
        self.assertEqual(meetings_per_judge[1], 2)
        self.assertEqual(meetings_per_judge[2], 2)
        self.assertEqual(meetings_per_judge[3], 2)
        
    def test_judge_with_zero_meetings(self):
        """
        Test the edge case where a judge is assigned 0 meetings.
        
        Scenario:
        - 3 judges with specific skills
        - 1 judge has skills that don't match any meetings
        - Meetings only require skills that the other 2 judges have
        
        Expected outcome:
        - 2 judges have meetings assigned
        - 1 judge has zero meetings assigned
        """
        # Create judges
        judges = [
            Judge(judge_id=1, judge_skills=[Sagstype.STRAFFE], judge_virtual=False),
            Judge(judge_id=2, judge_skills=[Sagstype.TVANG], judge_virtual=False),
            Judge(judge_id=3, judge_skills=[Sagstype.CIVIL], judge_virtual=False)  # No meetings need this skill
        ]
        
        # Create meetings - none require CIVIL
        meetings = [
            Meeting(meeting_id=1, meeting_duration=60, meeting_sagstype=Sagstype.STRAFFE, meeting_virtual=False),
            Meeting(meeting_id=2, meeting_duration=120, meeting_sagstype=Sagstype.STRAFFE, meeting_virtual=False),
            Meeting(meeting_id=3, meeting_duration=180, meeting_sagstype=Sagstype.TVANG, meeting_virtual=False),
            Meeting(meeting_id=4, meeting_duration=240, meeting_sagstype=Sagstype.TVANG, meeting_virtual=False),
        ]
        
        graph = DirectedGraph()
        graph.initialize_judge_case_graph(meetings, judges)
        
        # Assign meetings to judges
        judge_meeting_assignments: List[MeetingJudgeNode] = assign_judges_to_meetings(graph)
        meetings_per_judge = {judge.judge_id: 0 for judge in judges}
        for node in judge_meeting_assignments:
            meetings_per_judge[node.get_judge().judge_id] += 1
        
        # Verify assignments
        self.assertEqual(len(judge_meeting_assignments), 4, "All meetings should be assigned")
        self.assertEqual(meetings_per_judge[1], 2, "Judge 1 should have 2 STRAFFE meetings")
        self.assertEqual(meetings_per_judge[2], 2, "Judge 2 should have 2 TVANG meetings")
        self.assertEqual(meetings_per_judge[3], 0, "Judge 3 should have 0 meetings")
        
        

        
        