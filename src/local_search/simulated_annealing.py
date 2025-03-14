from src.base_model.schedule import Schedule
from src.base_model.appointment import Appointment
from src.base_model.room import Room
from src.base_model.judge import Judge
from rules_engine import calculate_score

class ShiftMove:
    def __init__(self, appointment: Appointment, to_timeslot: int):
        self.appointment = appointment
        self.to_timeslot = to_timeslot

class SwapMove:
    def __init__(self, chain1: list[Appointment], chain2: list[Appointment]):
        self.appointment1 = chain1
        self.appointment2 = chain2

class ReassignJudgeMove:
    def __init__(self, appointment: Appointment, new_judge: Judge):
        self.appointment = appointment
        self.new_judge = new_judge

class ReassignRoomMove:
    def __init__(self, appointment: Appointment, new_room: Room):
        self.appointment = appointment
        self.new_room = new_room
  


def calculate_alpha(K: int, start_temperature: int, end_temperature: int) -> int:
    """
    Calculate the alpha value for the simulated annealing algorithm.
    """
    return (end_temperature / start_temperature) ** (1 / (K -1))

def find_swap_moves(schedule: Schedule) -> list[SwapMove]:
    """
    Swap the assignments of two court cases by swapping start times.
    """
    swap_moves = []
    appointment_chains: dict = identify_appointment_chains(schedule)
    for chain1 in appointment_chains.values():
        for chain2 in appointment_chains.values():
            if chain1 == chain2:
                continue
            swap_moves.append(SwapMove(chain1, chain2))
            
        
    return swap_moves

# def find_split_moves(schedule: Schedule):
#     """
#     Split/merge move for longer cases split them into smaller or merge shorter cases
#     """
#     pass

def find_shift_moves(schedule: Schedule) -> list[ShiftMove]:
    """
    Move a courtcase to a different time
    """
    shift_moves = []

    appointment_chains: dict = identify_appointment_chains(schedule)    
    for i in len(appointment_chains):
        appointment_chain = appointment_chains[i]
        for day in range(schedule.work_days):
            for timeslot in range(schedule.timeslots_per_work_day):
                move = ShiftMove(appointment_chain[i], day * schedule.timeslots_per_work_day + timeslot)
                shift_moves.append(move)
    return shift_moves
    

def find_reassign_judge_moves(schedule: Schedule) -> list[ReassignJudgeMove]:
    """
    Change the judge
    """
    reassign_judge_moves = []
    judges = schedule.get_all_judges()
    
    for appointment in schedule.appointments:
        for judge in judges:
            move = ReassignJudgeMove(appointment, judge)
            reassign_judge_moves.append(move)
            
    return reassign_judge_moves

def find_reassign_room_moves(schedule: Schedule) -> list[ReassignRoomMove]:
    """
    Change the room
    """
    reassign_room_moves = []
    rooms = schedule.get_all_rooms()
    
    for appointment in schedule.appointments:
        for room in rooms:
            move = ReassignRoomMove(appointment, room)
            reassign_room_moves.append(move)
    
    return reassign_room_moves

def find_all_possible_moves(schedule: Schedule):
    """
    Find all possible neighbouring moves for the given schedule.
    """
    moves = []
    moves.extend(find_swap_moves(schedule))
    moves.extend(find_shift_moves(schedule))
    moves.extend(find_reassign_judge_moves(schedule))
    moves.extend(find_reassign_room_moves(schedule))
    
    return moves

def identify_appointment_chains(schedule: Schedule) -> dict[(int,int,int),list[Appointment]]:
    """
    Identify chains of appointments representing the same case-judge-room combination.
    
    Args:
        schedule: The current court schedule
        
    Returns:
        Dictionary mapping (case_id, judge_id, room_id) tuples to lists of appointments
    """
    appointment_chains: dict[(int,int,int),list[Appointment]] = {}  # Key: (case_id, judge_id, room_id), Value: list of appointments
    
    for appointment in schedule.appointments:
        key = (appointment.case.case_id, appointment.judge.judge_id, appointment.room.room_id)
        if key not in appointment_chains:
            appointment_chains[key] = []
        appointment_chains[key].append(appointment)
    
    # Sort each chain by absolute timeslot
    for key, appointments in appointment_chains.items():
        appointments.sort(key=lambda app: (app.day * schedule.timeslots_per_work_day + app.timeslot_start))
    
    return appointment_chains


def simulated_annealing(schedule: Schedule):
    pass

def run_local_search(schedule: Schedule) -> Schedule:
    """
    Run the simulated annealing algorithm to improve the given schedule.
    """
    num_cases = len(schedule.appointments)
    start_temperature = 250
    end_temperature = 1
    K = 100
    alpha = calculate_alpha(K, start_temperature, end_temperature)
    
    iterations_per_temperature = num_cases * (num_cases - 1) // 2
    
    
    pass
    
    