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
        
        # Store meeting state (judge/room assignments)
        self.meeting_states = {}
        for meeting in schedule.all_meetings:
            self.meeting_states[meeting.meeting_id] = (
                meeting.judge.judge_id if meeting.judge else None,
                meeting.room.room_id if meeting.room else None
            )
        
        # We don't need to deepcopy all cases - we just need to ensure 
        # we can properly restore the meeting references within them
    
    def restore_schedule(self, original_schedule):
        """Reconstruct a full Schedule object from this snapshot"""
        # Create a new schedule with the same parameters
        new_schedule = Schedule(self.work_days, self.minutes_in_a_work_day, self.granularity,
                               original_schedule.all_judges, original_schedule.all_rooms,
                               original_schedule.all_meetings, original_schedule.all_cases)
        
        # Lookup maps for faster restoration
        meetings_map = {m.meeting_id: m for m in original_schedule.all_meetings}
        judges_map = {j.judge_id: j for j in original_schedule.all_judges}
        rooms_map = {r.room_id: r for r in original_schedule.all_rooms}
        
        # First, restore the meeting state (judge/room assignments)
        for meeting_id, (judge_id, room_id) in self.meeting_states.items():
            meeting = meetings_map[meeting_id]
            meeting.judge = judges_map[judge_id] if judge_id is not None else None
            meeting.room = rooms_map[room_id] if room_id is not None else None
        
        # Restore appointments
        for meeting_id, judge_id, room_id, day, timeslot in self.appointments:
            meeting = meetings_map[meeting_id]
            judge = judges_map[judge_id]
            room = rooms_map[room_id]
            
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
    
