from src.base_model.schedule import Schedule
from src.base_model.meeting import Meeting
from src.base_model.appointment import Appointment
from typing import List, Tuple

class Move:
    def __init__(self, meeting_id, appointments: list[Appointment],
                 old_judge=None, new_judge=None,
                 old_room=None, new_room=None,
                 old_day=None, new_day=None,
                 old_start_timeslot=None, new_start_timeslot=None,
                 is_delete_move=False, is_insert_move=False):
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
        self.is_delete_move = is_delete_move
        self.is_insert_move = is_insert_move
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
        if self.appointments:
            move_type.append(f"appointments={len(self.appointments)}")
        if self.is_delete_move:
            move_type.append("delete")
        if self.is_insert_move:
            move_type.append("insert")

        return f"Move(meeting {self.meeting_id}: {', '.join(move_type)})"


def do_move(move: Move, schedule: Schedule = None) -> None:
    """Update appointments and the schedule dictionary if provided"""
    if move.is_applied:
        return
    
    # Handle insertion move
    elif move.is_insert_move:
        if schedule is None:
            raise ValueError("Schedule must be provided to do insertion move.")
        
        # Get the meeting from unplanned meetings
        try:
            meeting = schedule.pop_meeting_from_unplanned_meetings(move.meeting_id)
        except ValueError:
            raise ValueError(f"Meeting with ID {move.meeting_id} not found in unplanned meetings.")
        
        # Set the judge and room on the meeting
        meeting.judge = move.new_judge
        meeting.room = move.new_room
        
        # Calculate the number of timeslots needed for this meeting
        if schedule.granularity == 0 or meeting.meeting_duration <= 0:
            raise ValueError("Granularity must be greater than 0 and meeting duration must be positive.")
        timeslots_needed = (meeting.meeting_duration // schedule.granularity) 
        
        # Create appointment objects for each timeslot
        for i in range(timeslots_needed):
            global_timeslot = ((move.new_day - 1) * schedule.timeslots_per_work_day) + move.new_start_timeslot + i
            day = ((global_timeslot - 1) // schedule.timeslots_per_work_day) + 1
            timeslot_in_day = ((global_timeslot - 1) % schedule.timeslots_per_work_day) + 1
            
            appointment = Appointment(
                meeting=meeting,
                judge=move.new_judge,
                room=move.new_room,
                day=day,
                timeslot_in_day=timeslot_in_day
            )
            
            appointment.meeting.judge = appointment.judge
            appointment.meeting.room = appointment.room
            
            move.appointments.append(appointment)
            
            if day not in schedule.appointments_by_day_and_timeslot:
                schedule.appointments_by_day_and_timeslot[day] = {}
            if timeslot_in_day not in schedule.appointments_by_day_and_timeslot[day]:
                schedule.appointments_by_day_and_timeslot[day][timeslot_in_day] = []
            
            schedule.appointments_by_day_and_timeslot[day][timeslot_in_day].append(appointment)
        
        max_day = max(app.day for app in move.appointments)
        if max_day > schedule.work_days:
            schedule.work_days = max_day
        
        # Add the appointment chain to schedule
        if schedule is not None and move.appointments:
            schedule.appointment_chains[move.meeting_id] = move.appointments
            
        move.is_applied = True
        return

    # Handle deletion move
    elif move.is_delete_move:
        if schedule is None:
            raise ValueError("Schedule must be provided for delete move.")
        for app in move.appointments:
            appointments = schedule.appointments_by_day_and_timeslot[app.day][app.timeslot_in_day]
            index = next((i for i, appointment in enumerate(appointments) if appointment is app), None)
            if index is not None:
                appointments.pop(index)
            else:
                raise ValueError(f"Appointment {app} not found in schedule.")
            
        # adding it to the unplanned meetings
        if schedule is not None and move.appointments:
            # nullify the judge and room (no longer assigned)
            move.appointments[0].meeting.judge = None
            move.appointments[0].meeting.room = None
            schedule.add_to_unplanned_meetings(move.appointments[0].meeting)
            
            # Remove the appointment chain from schedule
            if move.meeting_id in schedule.appointment_chains:
                del schedule.appointment_chains[move.meeting_id]
            
        move.is_applied = True
        if schedule is not None:
            schedule.trim_schedule_length_if_possible()
        return

    # Handle regular move
    else:
        changing_position = (move.new_day is not None or move.new_start_timeslot is not None)

        for i, app in enumerate(move.appointments):
            # update the dict - remove the appointments from the old position
            if schedule is not None and changing_position:
                old_day = app.day
                old_timeslot = app.timeslot_in_day

                appointments = schedule.appointments_by_day_and_timeslot[old_day][old_timeslot]
                index = next((i for i, appointment in enumerate(appointments) if appointment is app), None)
                if index is not None:
                    appointments.pop(index)
                else:
                    print(f"Appointment {app} not found in schedule.") 
                    raise ValueError(f"Appointment {app} not found in schedule.")
                        
            if move.new_judge is not None:
                app.judge = move.new_judge
                app.meeting.judge = move.new_judge #sync

            if move.new_room is not None:
                app.room = move.new_room
                app.meeting.room = move.new_room #sync

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

                if new_day not in schedule.appointments_by_day_and_timeslot:
                    schedule.appointments_by_day_and_timeslot[new_day] = {}
                if new_timeslot not in schedule.appointments_by_day_and_timeslot[new_day]:
                    schedule.appointments_by_day_and_timeslot[new_day][new_timeslot] = []
                    
                # if app in schedule.appointments_by_day_and_timeslot[new_day][new_timeslot]:
                #     raise ValueError(f"Appointment {app} already exists in the new position.") # shouldnt happen but good for safety

                schedule.appointments_by_day_and_timeslot[new_day][new_timeslot].append(app)

        move.is_applied = True        
        
        if schedule is not None:
            schedule.trim_schedule_length_if_possible()        

def undo_move(move: Move, schedule: Schedule = None) -> None:
    """Undo a move and update the schedule dictionary if provided"""
    if not move.is_applied:
        return
    
    # Handle insertion moves
    elif move.is_insert_move:
        if schedule is None:
            raise ValueError("Schedule must be provided for undo insertion move.")
        
        # Remove all appointments from the schedule
        for app in move.appointments:
            if (app.day in schedule.appointments_by_day_and_timeslot and
                app.timeslot_in_day in schedule.appointments_by_day_and_timeslot[app.day] and
                app in schedule.appointments_by_day_and_timeslot[app.day][app.timeslot_in_day]):
                
                schedule.appointments_by_day_and_timeslot[app.day][app.timeslot_in_day].remove(app)
        
        # Get the meeting from the first appointment
        if move.appointments:
            meeting = move.appointments[0].meeting
            # Reset judge and room
            meeting.judge = None
            meeting.room = None
            # Add back to unplanned meetings
            schedule.add_to_unplanned_meetings(meeting)
            
            # Remove the appointment chain from schedule
            if move.meeting_id in schedule.appointment_chains:
                del schedule.appointment_chains[move.meeting_id]
        
        move.is_applied = False
        if schedule is not None:
            schedule.trim_schedule_length_if_possible()
        return
        

    # Handle deletion move
    elif move.is_delete_move:
        
        # remove the meeting from the unplanned meetings
        if schedule is not None and move.appointments:
            meeting_to_restore = move.appointments[0].meeting
            meeting_id = meeting_to_restore.meeting_id
            try:
                schedule.pop_meeting_from_unplanned_meetings(meeting_id)
                meeting_to_restore.judge = move.old_judge
                meeting_to_restore.room = move.old_room
            except ValueError:
                raise ValueError(f"Meeting with id {meeting_id} not found in unplanned meetings.")
        
        # adding the appointments back to the schedule
        for app in move.appointments:
            if schedule is None:
                raise ValueError("Schedule must be provided for undo delete move.")
            
            # setting the fields of app just in case
            app.judge = move.old_judge
            app.room = move.old_room
            app.day = move.old_day
            app.timeslot_in_day = move.old_start_timeslot + move.appointments.index(app)
            
            day_to_add = app.day
            timeslot_to_add = app.timeslot_in_day
            
            if day_to_add not in schedule.appointments_by_day_and_timeslot:
                schedule.appointments_by_day_and_timeslot[app.day] = {}
            if timeslot_to_add not in schedule.appointments_by_day_and_timeslot[app.day]:
                schedule.appointments_by_day_and_timeslot[app.day][app.timeslot_in_day] = []
            
            # if app in schedule.appointments_by_day_and_timeslot[app.day][app.timeslot_in_day]:
            #     raise ValueError(f"Appointment {app} already exists in the new position.") # shouldnt happen but good for safety
            
            schedule.appointments_by_day_and_timeslot[app.day][app.timeslot_in_day].append(app)
        
        # Restore the appointment chain
        if schedule is not None and move.appointments:
            schedule.appointment_chains[move.meeting_id] = move.appointments
        
        move.is_applied = False
        return # trimming is not needed because adding meetings into the schedule will never make it shorter
        
    # Handle regular move
    else:
        changing_position = (move.new_day is not None or move.new_start_timeslot is not None)
        
        for i, app in enumerate(move.appointments):
            # update the dict - remove the appointments from the new position
            if schedule is not None and changing_position:
                current_day = app.day
                current_timeslot = app.timeslot_in_day

                appointments = schedule.appointments_by_day_and_timeslot[current_day][current_timeslot]
                index = next((i for i, appointment in enumerate(appointments) if appointment is app), None)
                if index is not None:
                    appointments.pop(index)
                else:
                    raise ValueError(f"Appointment {app} not found in schedule.")

            if move.old_judge is not None:
                app.judge = move.old_judge
                app.meeting.judge = move.old_judge #sync

            if move.old_room is not None:
                app.room = move.old_room
                app.meeting.room = move.old_room #sync

            if move.new_day is not None:  # Only restore day if it was actually changed
                app.day = move.old_day

            if move.old_start_timeslot is not None:
                start_day = move.old_day if move.old_day is not None else app.day
                start_timeslot = move.old_start_timeslot if move.old_start_timeslot is not None else app.timeslot_in_day
                global_timeslot = ((start_day - 1) * schedule.timeslots_per_work_day) + start_timeslot + i

                app.day = ((global_timeslot - 1) // schedule.timeslots_per_work_day) + 1
                app.timeslot_in_day = ((global_timeslot - 1) % schedule.timeslots_per_work_day) + 1
                    
                # Extend schedule if needed
                if schedule is not None and app.day > schedule.work_days:
                    schedule.work_days = app.day

            # update the dict - add the appointments to the old position
            if schedule is not None and changing_position:
                original_day = app.day
                original_timeslot = app.timeslot_in_day

                if original_day not in schedule.appointments_by_day_and_timeslot:
                    schedule.appointments_by_day_and_timeslot[original_day] = {}
                if original_timeslot not in schedule.appointments_by_day_and_timeslot[original_day]:
                    schedule.appointments_by_day_and_timeslot[original_day][original_timeslot] = []

                schedule.appointments_by_day_and_timeslot[original_day][original_timeslot].append(app)

        move.is_applied = False
            
        if schedule is not None:
            schedule.trim_schedule_length_if_possible()


class ContractingMove:
    """
    A compound move that contracts the schedule by moving meetings earlier in the day
    when possible, respecting room availability constraints.
    """
    def __init__(self):
        self.individual_moves: List[Move] = []  # List of moves to be applied
        self.skipped_meetings: List[Tuple[int, str]] = []  # List of (meeting_id, reason) tuples
        self.is_applied = False
    
    def add_move(self, move: Move):
        """Add an individual move to the contracting move."""
        self.individual_moves.append(move)
    
    def add_skipped(self, meeting_id: int, reason: str):
        """Track a meeting that was skipped and why."""
        self.skipped_meetings.append((meeting_id, reason))
    
    def __str__(self):
        return f"ContractingMove(moves={len(self.individual_moves)}, skipped={len(self.skipped_meetings)})"
    
    def get_summary(self):
        """Get a detailed summary of the contracting move."""
        summary = f"Contracting Move Summary:\n"
        summary += f"  - Total moves: {len(self.individual_moves)}\n"
        summary += f"  - Skipped meetings: {len(self.skipped_meetings)}\n"
        
        if self.individual_moves:
            summary += "\nMoves applied:\n"
            for move in self.individual_moves[:5]:  # Show first 5
                summary += f"  - Meeting {move.meeting_id}: timeslot {move.old_start_timeslot} → {move.new_start_timeslot}\n"
            if len(self.individual_moves) > 5:
                summary += f"  ... and {len(self.individual_moves) - 5} more\n"
        
        if self.skipped_meetings:
            summary += "\nSkipped meetings:\n"
            for meeting_id, reason in self.skipped_meetings[:5]:  # Show first 5
                summary += f"  - Meeting {meeting_id}: {reason}\n"
            if len(self.skipped_meetings) > 5:
                summary += f"  ... and {len(self.skipped_meetings) - 5} more\n"
        
        return summary


def do_contracting_move(contracting_move: ContractingMove, schedule: Schedule) -> None:
    """Apply all individual moves in the contracting move."""
    if contracting_move.is_applied:
        return
    
    for move in contracting_move.individual_moves:
        do_move(move, schedule)
    
    contracting_move.is_applied = True


def undo_contracting_move(contracting_move: ContractingMove, schedule: Schedule) -> None:
    """Undo all individual moves in the contracting move in reverse order."""
    if not contracting_move.is_applied:
        return
    
    # Undo in reverse order to maintain consistency
    for move in reversed(contracting_move.individual_moves):
        # Force reset the is_applied flag since moves were applied during generation
        move.is_applied = True
        undo_move(move, schedule)
    
    contracting_move.is_applied = False        