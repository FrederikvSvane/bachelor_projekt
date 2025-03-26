class Move:
    def __init__(self, meeting_id, appointments, 
                 old_judge=None, new_judge=None, 
                 old_room=None, new_room=None,
                 old_day=None, new_day=None,
                 old_start_timeslot=None, new_start_timeslot=None,
                 timeslots_per_day=None):
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
        self.timeslots_per_day = timeslots_per_day
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
        
        return f"Move(case {self.meeting_id}: {', '.join(move_type)})"


def do_move(move: Move) -> None:
    """Apply a move to the schedule"""
    if move.is_applied:
        return
        
    if move.new_judge:
        for app in move.appointments:
            app.judge = move.new_judge
            
    if move.new_room:
        for app in move.appointments:
            app.room = move.new_room
            
    if move.new_day is not None:
        for app in move.appointments:
            app.day = move.new_day
    
    if move.new_start_timeslot is not None:
        for i, app in enumerate(move.appointments):
            app.timeslot_in_day = move.new_start_timeslot + i
            
    move.is_applied = True


def undo_move(move: Move) -> None:
    """Undo a previously applied move"""
    if not move.is_applied:
        return
        
    if move.old_judge:
        for app in move.appointments:
            app.judge = move.old_judge
            
    if move.old_room:
        for app in move.appointments:
            app.room = move.old_room
    
    if move.old_day is not None:
        for app in move.appointments:
            app.day = move.old_day
            
    if move.old_start_timeslot is not None:
        for i, app in enumerate(move.appointments):
            app.timeslot_in_day = move.old_start_timeslot + i
            
    move.is_applied = False