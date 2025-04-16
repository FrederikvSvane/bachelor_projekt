import random
from typing import Dict, List

from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.case import Case
from src.base_model.meeting import Meeting
from src.base_model.appointment import Appointment
from src.base_model.schedule import Schedule
from src.base_model.compatibility_checks import calculate_compatible_judges, calculate_compatible_rooms

def add_meeting_to_schedule(schedule: Schedule, meeting: Meeting, compatible_judges_dict: dict[int, list[Judge]], compatible_rooms_dict: dict[int, list[Room]]):
    meeting_length = meeting.meeting_duration // schedule.granularity
    if meeting_length <= 0:
         return

    if meeting.meeting_id not in compatible_judges_dict or not compatible_judges_dict[meeting.meeting_id]:
        print(f"Error: No compatible judges for meeting {meeting.meeting_id}. Skipping placement.")
        return
    if meeting.meeting_id not in compatible_rooms_dict or not compatible_rooms_dict[meeting.meeting_id]:
        print(f"Error: No compatible rooms for meeting {meeting.meeting_id}. Skipping placement.")
        return

    judges = compatible_judges_dict[meeting.meeting_id]
    rooms = compatible_rooms_dict[meeting.meeting_id]

    selected_day = random.randint(1, schedule.work_days)

    max_start_timeslot = schedule.timeslots_per_work_day - meeting_length + 1
    if max_start_timeslot < 1:
        print(f"Error: Meeting {meeting.meeting_id} duration ({meeting_length} slots) is too long for a single day ({schedule.timeslots_per_work_day} slots). Skipping placement.")
        return
    selected_start_timeslot = random.randint(1, max_start_timeslot)

    selected_judge = random.choice(judges)
    selected_room = random.choice(rooms)

    for i in range(meeting_length):
        current_timeslot = selected_start_timeslot + i

        appointment_part = Appointment(
            meeting=meeting,
            judge=selected_judge,
            room=selected_room,
            day=selected_day,
            timeslot_in_day=current_timeslot
        )
        schedule.add_meeting_to_schedule(appointment_part)

        meeting.judge = selected_judge
        meeting.room = selected_room


def generate_schedule(parsed_data: dict) -> Schedule:
    cases: list[Case] = parsed_data["cases"]
    judges: list[Judge] = parsed_data["judges"]
    rooms: list[Room] = parsed_data["rooms"]
    work_days: int = parsed_data["work_days"]
    min_per_work_day: int = parsed_data["min_per_work_day"]
    granularity: int = parsed_data["granularity"]


    meetings: list[Meeting] = []
    for case in cases:
        meetings.extend(case.meetings)

    print(f"Number of meetings: {len(meetings)}")
    if not meetings:
         print("Warning: No meetings found in the parsed data.")
         return Schedule(work_days, min_per_work_day, granularity, judges, rooms)

    compatible_judges_dict = calculate_compatible_judges(meetings, judges)
    compatible_rooms_dict = calculate_compatible_rooms(meetings, rooms)

    schedule = Schedule(work_days, min_per_work_day, granularity, judges, rooms)

    meetings_to_schedule = list(meetings)
    meetings_to_schedule.sort(key=lambda x: x.meeting_duration, reverse=True)

    for meeting in meetings_to_schedule:
        add_meeting_to_schedule(schedule, meeting, compatible_judges_dict, compatible_rooms_dict)
        
        
    return schedule