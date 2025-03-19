from src.base_model.schedule import Schedule
from src.base_model.appointment import Appointment, print_appointments
from src.base_model.compatibility_checks import case_judge_compatible, case_room_compatible
from src.base_model.case import Case
from src.base_model.room import Room
from src.base_model.judge import Judge
from src.local_search.rules_engine import calculate_score
import random



class SwapMove:
    def __init__(self, judge_swap: bool, room_swap: bool, time_swap: bool):
        self.judge_swap = judge_swap
        self.room_swap = room_swap
        self.time_swap = time_swap

    def print_move(self):
        print(f"Judge swap: {self.judge_swap}, Room swap: {self.room_swap}, Time swap: {self.time_swap}")
        

def calculate_alpha(K: int, start_temperature: int, end_temperature: int) -> int:
    """
    Calculate the alpha value for the simulated annealing algorithm.
    """
    return (end_temperature / start_temperature) ** (1 / (K -1))


def find_all_possible_moves():
    """
    Find all possible neighbouring moves for the given schedule.
    """
    moves = []
    for i in [True, False]:
        for j in [True, False]:
            for k in [True, False]:
                moves.append(SwapMove(i,j,k))

    return moves

def identify_appointment_chains(schedule: Schedule) -> dict[int, list[Appointment]]:
    """
    Identify chains of appointments representing the same case-judge-room combination.
    
    Args:
        schedule: The current court schedule
        
    Returns:
        Dictionary mapping (case_id, judge_id, room_id) tuples to lists of appointments
    """
    appointment_chains: dict[int, list[Appointment]] = {}  # Key: (case_id), Value: list of appointments
    
    for appointment in schedule.appointments:
        key = (appointment.case.case_id)
        if key not in appointment_chains:
            appointment_chains[key] = []
        appointment_chains[key].append(appointment)
    
    # Sort each chain by absolute timeslot
    for key, appointments in appointment_chains.items():
        appointments.sort(key=lambda app: (app.day * schedule.timeslots_per_work_day + app.timeslot_start))
    
    return appointment_chains


def select_random_move(moves: list[SwapMove]) -> SwapMove:
    return random.choice(moves)

def select_random_case(cases: list[Case]) -> Case:
    return random.choice(cases)

def select_random_judge(judges: list[Judge], appointment: Appointment) -> Judge:
    available_judges = [judge for judge in judges if appointment.judge != judge]
    if not available_judges:
        return appointment.judge
    return random.choice(available_judges)

def select_random_room(rooms: list[Room], appointment: Appointment) -> Room:
    available_rooms = [room for room in rooms if appointment.room != room]
    if not available_rooms:
        return appointment.room
    return random.choice(available_rooms)
    
def select_random_time(timeslots: int, appointment: Appointment) -> int:
    available_timeslots = [timeslot for timeslot in range(timeslots + 1) if appointment.timeslot_start != timeslot]
    return random.choice(available_timeslots)

def swap_judge(case_chain: list[Appointment], judge: Judge) -> None:
    for appointment in case_chain:
        appointment.judge = judge

def swap_room(case_chain: list[Appointment], room: Room) -> None:
    for appointment in case_chain:
        appointment.room = room

def swap_time(case_chain: list[Appointment], timeslot: int) -> None:
    for i, appointment in enumerate(case_chain):
        appointment.timeslot_start = timeslot + i

def calculate_compatible_judges(cases: list[Case], judges: list[Judge]) -> dict[int, list[Judge]]:
    compatible_judges: dict[int, list[Judge]] = {}
    for case in cases:
        compatible_judges[case.case_id] = [judge for judge in judges if case_judge_compatible(case, judge)]
        
    return compatible_judges

def calculate_compatible_rooms(cases: list[Case], rooms: list[Room]) -> dict[int, list[Room]]:
    compatible_rooms: dict[int, list[Room]] = {}
    for case in cases:
        compatible_rooms[case.case_id] = [room for room in rooms if case_room_compatible(case, room)]
        
    return compatible_rooms

def process_move(move: SwapMove, case_chain: list[Appointment], judges: list[Judge], rooms: list[Room], timeslots: list[int]) -> list[Appointment]:
    appointment: Appointment = case_chain[0]
    match move:
        case SwapMove(judge_swap = True, room_swap = False, time_swap = False):
            judge: Judge = select_random_judge(judges, appointment)
            swap_judge(case_chain, judge)
        case SwapMove(judge_swap = False, room_swap = True, time_swap = False):
            room: Room = select_random_room(rooms, appointment)
            swap_room(case_chain, room)
        case SwapMove(judge_swap = False, room_swap = False, time_swap = True):
            timeslot: int = select_random_time(timeslots, appointment)
            swap_time(case_chain, timeslot)
        case SwapMove(judge_swap = True, room_swap = True, time_swap = False):
            judge: Judge = select_random_judge(judges, appointment)
            room: Room = select_random_room(rooms, appointment)
            swap_judge(case_chain, judge)
            swap_room(case_chain, room)
        case SwapMove(judge_swap = True, room_swap = False, time_swap = True):
            judge: Judge = select_random_judge(judges, appointment)
            timeslot: int = select_random_time(timeslots, appointment)
            swap_judge(case_chain, judge)
            swap_time(case_chain, timeslot)
        case SwapMove(judge_swap = False, room_swap = True, time_swap = True):
            room: Room = select_random_room(rooms, appointment)
            timeslot: int = select_random_time(timeslots, appointment)
            swap_room(case_chain, room)
            swap_time(case_chain, timeslot)
        case SwapMove(judge_swap = True, room_swap = True, time_swap = True):
            judge: Judge = select_random_judge(judges, appointment)
            room: Room = select_random_room(rooms, appointment)
            timeslot: int = select_random_time(timeslots, appointment)
            swap_judge(case_chain, judge)
            swap_room(case_chain, room)
            swap_time(case_chain, timeslot)
        case SwapMove(judge_swap = False, room_swap = False, time_swap = False):
            print("Stoopid move")
        case _:
            print("Invalid move")
    return case_chain
    

def simulated_annealing(schedule: Schedule):
    num_cases = len(schedule.get_all_cases())
    iterations_per_temperature = num_cases * (num_cases - 1) // 2
    start_temperature = 250
    end_temperature = 1
    K = 100
    alpha = calculate_alpha(K, start_temperature, end_temperature)
    pass

def run_local_search(schedule: Schedule) -> Schedule:
    """
    Run the simulated annealing algorithm to improve the given schedule.
    """
    cases: list[Case]  = schedule.get_all_cases()
    judges: list[Judge] = schedule.get_all_judges()
    rooms: list[Room] = schedule.get_all_rooms() 
    compatible_judges: dict[int, list[Judge]] = calculate_compatible_judges(cases, judges)
    compatible_rooms: dict[int, list[Room]] = calculate_compatible_rooms(cases, rooms) 
    timeslots = schedule.timeslots_per_work_day * schedule.work_days
    
    chain_dict = identify_appointment_chains(schedule)
    
    moves = find_all_possible_moves()
    
    chosen_case: Case = select_random_case(cases)
    chosen_case_chain: list[Appointment] = chain_dict[chosen_case.case_id]
    chosen_move: SwapMove = select_random_move(moves)
    
    print("chosen chain before modification:")
    print_appointments(chosen_case_chain)
    
    judges.remove(chosen_case_chain[0].judge)
    rooms.remove(chosen_case_chain[0].room)
    modified_case_chain: list[Appointment] = process_move(chosen_move, chosen_case_chain, judges, rooms, timeslots)
    
    
    print("chosen chain after modification:")
    print_appointments(modified_case_chain)
    
    
    
    
    
    
    

    
    