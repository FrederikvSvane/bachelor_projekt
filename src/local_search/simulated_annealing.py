from src.base_model.schedule import Schedule
from src.base_model.appointment import Appointment, print_appointments
from src.base_model.case import Case
from src.base_model.room import Room
from src.base_model.judge import Judge
from src.local_search.rules_engine import calculate_score



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


def simulated_annealing(schedule: Schedule):
    pass

def run_local_search(schedule: Schedule) -> Schedule:
    """
    Run the simulated annealing algorithm to improve the given schedule.
    """
    cases: list[Case]  = schedule.get_all_cases()
    judges: list[Judge] = schedule.get_all_judges()
    rooms: list[Room] = schedule.get_all_rooms() 
    num_cases = len(cases)
    
    chain_dict = identify_appointment_chains(schedule)
    
    start_temperature = 250
    end_temperature = 1
    K = 100
    alpha = calculate_alpha(K, start_temperature, end_temperature)
    
    moves = find_all_possible_moves()
    
    #print_appointments(schedule.appointments)
    
    
    iterations_per_temperature = num_cases * (num_cases - 1) // 2
    
    

    
    