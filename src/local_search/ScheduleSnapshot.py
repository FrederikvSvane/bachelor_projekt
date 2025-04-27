from src.base_model.schedule import Schedule
from src.base_model.appointment import Appointment
class ScheduleSnapshot:
    def __init__(self, schedule):
        self.work_days = schedule.work_days
        self.minutes_in_a_work_day = schedule.minutes_in_a_work_day
        self.granularity = schedule.granularity
        
        # Store appointments as (meeting_id, judge_id, room_id, day, timeslot)
        self.appointments = []
        for app in schedule.iter_appointments():
            self.appointments.append((
                app.meeting.meeting_id,
                app.judge.judge_id,
                app.room.room_id,
                app.day,
                app.timeslot_in_day
            ))
        
        # Store unplanned meetings
        self.unplanned_meeting_ids = [m.meeting_id for m in schedule.unplanned_meetings]
        
        # Store case-meeting-judge relationships
        self.case_meeting_details = {}
        for case in schedule.all_cases:
            self.case_meeting_details[case.case_id] = {
                m.meeting_id: (
                    m.judge.judge_id if m.judge else None,
                    m.room.room_id if m.room else None
                ) for m in case.meetings
            }
        
    def restore_schedule(self, original_schedule):
        """Reconstruct a full Schedule object from this snapshot"""
        # Create a new schedule with the same parameters - use original cases
        new_schedule = Schedule(
            self.work_days, 
            self.minutes_in_a_work_day, 
            self.granularity,
            original_schedule.all_judges, 
            original_schedule.all_rooms,
            original_schedule.all_meetings, 
            original_schedule.all_cases
        )
        
        # Lookup maps for faster restoration
        meetings_map = {m.meeting_id: m for m in original_schedule.all_meetings}
        judges_map = {j.judge_id: j for j in original_schedule.all_judges}
        rooms_map = {r.room_id: r for r in original_schedule.all_rooms}
        
        # First, restore case-meeting-judge-room relationships
        for _, meeting_details in self.case_meeting_details.items():
            for meeting_id, (judge_id, room_id) in meeting_details.items():
                meeting = meetings_map[meeting_id]
                meeting.judge = judges_map[judge_id] if judge_id is not None else None
                meeting.room = rooms_map[room_id] if room_id is not None else None
                
        # Restore appointments
        for meeting_id, judge_id, room_id, day, timeslot in self.appointments:
            meeting = meetings_map[meeting_id]
            judge = judges_map[judge_id]
            room = rooms_map[room_id]
            
            # Set meeting's room
            meeting.room = room
            
            # Create and add appointment
            app = Appointment(meeting, judge, room, day, timeslot)
            new_schedule.add_meeting_to_schedule(app)
        
        # Restore unplanned meetings
        for meeting_id in self.unplanned_meeting_ids:
            meeting = meetings_map[meeting_id]
            new_schedule.add_to_unplanned_meetings(meeting)
        
        # Initialize chains
        new_schedule.initialize_appointment_chains()
        
        return new_schedule