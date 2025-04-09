from src.base_model.schedule import Schedule
from src.base_model.meeting import Meeting
from src.base_model.appointment import Appointment

class Move:
    def __init__(self, meeting_id, appointments: list[Appointment],
                 old_judge=None, new_judge=None,
                 old_room=None, new_room=None,
                 old_day=None, new_day=None,
                 old_start_timeslot=None, new_start_timeslot=None):
        self.meeting_id = meeting_id
        self.appointments = appointments  # List of affected appointments
        self.old_judge = old_judge
        self.new_judge = new_judge
        self.old_room = old_room
        self.new_room = new_room
        self.old_day = old_day
        self.new_day = new_day
        self.old_start_timeslot = old_start_timeslot  # 1-indexed timeslot within day
        self.new_start_timeslot = new_start_timeslot  # 1-indexed timeslot within day
        self.is_applied = False

    def __str__(self):
        move_type = []
        if self.new_judge:
            move_type.append(f"judge {self.old_judge} → {self.new_judge}")
        if self.new_room:
            move_type.append(f"room {self.old_room} → {self.new_room}")
        if self.new_day is not None:
            move_type.append(f"day {self.old_day} → {self.new_day}")
        if self.new_start_timeslot is not None:
            move_type.append(f"timeslot {self.old_start_timeslot} → {self.new_start_timeslot}")

        return f"Move(meeting {self.meeting_id}: {', '.join(move_type)})"


def do_move(move: Move, schedule: Schedule = None) -> None:
    """Update appointments and the schedule dictionary if provided"""
    if move.is_applied:
        return

    changing_position = (move.new_day is not None or move.new_start_timeslot is not None)

    for i, app in enumerate(move.appointments):
        # update the dict - remove the appointments from the old position
        if schedule is not None and changing_position:
            old_day = app.day
            old_timeslot = app.timeslot_in_day
            if (old_day in schedule.appointments_by_day and
                old_timeslot in schedule.appointments_by_day[old_day]):
                schedule.appointments_by_day[old_day][old_timeslot].remove(app)

        if move.new_judge is not None:
            app.judge = move.new_judge

        if move.new_room is not None:
            app.room = move.new_room

        if move.new_day is not None:
            app.day = move.new_day

        if move.new_start_timeslot is not None or move.new_day is not None:
            start_day = move.new_day if move.new_day is not None else move.old_day
            start_timeslot = move.new_start_timeslot if move.new_start_timeslot is not None else move.old_start_timeslot
            global_timeslot = ((start_day - 1) * schedule.timeslots_per_work_day) + start_timeslot + i

            app.day = ((global_timeslot - 1) // schedule.timeslots_per_work_day) + 1
            app.timeslot_in_day = ((global_timeslot - 1) % schedule.timeslots_per_work_day) + 1

            # Extend schedule if needed
            if schedule is not None and app.day > schedule.work_days:
                schedule.work_days = app.day

        # update the dict - add the appointments to the new position
        if schedule is not None and changing_position:
            new_day = app.day
            new_timeslot = app.timeslot_in_day

            if new_day not in schedule.appointments_by_day:
                schedule.appointments_by_day[new_day] = {}
            if new_timeslot not in schedule.appointments_by_day[new_day]:
                schedule.appointments_by_day[new_day][new_timeslot] = []

            schedule.appointments_by_day[new_day][new_timeslot].append(app)

    move.is_applied = True
    
    if schedule is not None:
        schedule.trim_schedule_length_if_possible()        

def undo_move(move: Move, schedule: Schedule = None) -> None:
    """Undo a move and update the schedule dictionary if provided"""
    if not move.is_applied:
        return

    changing_position = (move.old_day is not None or move.old_start_timeslot is not None)

    for i, app in enumerate(move.appointments):
        # update the dict - remove the appointments from the new position
        if schedule is not None and changing_position:
            current_day = app.day
            current_timeslot = app.timeslot_in_day
            if (current_day in schedule.appointments_by_day and
                current_timeslot in schedule.appointments_by_day[current_day]):
                schedule.appointments_by_day[current_day][current_timeslot].remove(app)

        if move.old_judge is not None:
            app.judge = move.old_judge

        if move.old_room is not None:
            app.room = move.old_room

        if move.old_day is not None:
            app.day = move.old_day

        if move.old_start_timeslot is not None:
            new_timeslot = move.old_start_timeslot + i

            day_offset = (new_timeslot - 1) // schedule.timeslots_per_work_day
            adjusted_timeslot = ((new_timeslot - 1) % schedule.timeslots_per_work_day) + 1

            if day_offset > 0:
                app.day = move.old_day + day_offset if move.old_day is not None else app.day + day_offset
                app.timeslot_in_day = adjusted_timeslot
            else:
                app.timeslot_in_day = new_timeslot
                
            # Extend schedule if needed
            if schedule is not None and app.day > schedule.work_days:
                schedule.work_days = app.day

        # update the dict - add the appointments to the old position
        if schedule is not None and changing_position:
            original_day = app.day
            original_timeslot = app.timeslot_in_day

            if original_day not in schedule.appointments_by_day:
                schedule.appointments_by_day[original_day] = {}
            if original_timeslot not in schedule.appointments_by_day[original_day]:
                schedule.appointments_by_day[original_day][original_timeslot] = []

            schedule.appointments_by_day[original_day][original_timeslot].append(app)

    move.is_applied = False
    
    # Shrink schedule if the last day is empty
    if schedule is not None:
        schedule.trim_schedule_length_if_possible()        