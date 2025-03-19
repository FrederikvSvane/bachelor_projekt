from src.base_model.schedule import Schedule
from src.base_model.appointment import Appointment, print_appointments
from src.util.schedule_visualizer import visualize
from src.base_model.compatibility_checks import case_judge_compatible, case_room_compatible
from src.base_model.case import Case
from src.base_model.room import Room
from src.base_model.judge import Judge
from src.local_search.rules_engine import calculate_score, print_score_summary
import random
from copy import deepcopy
import math



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
        appointments.sort(key=lambda app: ((app.day - 1) * schedule.timeslots_per_work_day + app.timeslot_in_day))
    
    return appointment_chains


def select_random_move(moves: list[SwapMove]) -> SwapMove:
    return random.choice(moves)

def select_random_case(cases: list[int]) -> Case:
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
    #Maybe dont work
    #TODO make sure doesnt not exceed schedule and is within day
    available_timeslots = [timeslot for timeslot in range(timeslots + 1) if appointment.timeslot_in_day != timeslot]
    return random.choice(available_timeslots)

def swap_judge(case_chain: list[Appointment], judge: Judge) -> None:
    for appointment in case_chain:
        appointment.judge = judge

def swap_room(case_chain: list[Appointment], room: Room) -> None:
    for appointment in case_chain:
        appointment.room = room

def swap_time(case_chain: list[Appointment], timeslot: int) -> None:
    for i, appointment in enumerate(case_chain):
        appointment.timeslot_in_day = timeslot + i
        appointment.day = appointment.timeslot_in_day // 78
        
        
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

def process_move(move: SwapMove, case_chain: list[Appointment], compatible_judges: list[Judge], compatible_rooms: list[Room], timeslots: int) -> None:
    appointment: Appointment = case_chain[0]
    case: Case = appointment.case
    
    if move.judge_swap and compatible_judges:
        new_judge = select_random_judge(compatible_judges, appointment)
        swap_judge(case_chain, new_judge)
        
    if move.room_swap and compatible_rooms:
        new_room = select_random_room(compatible_rooms, appointment)
        swap_room(case_chain, new_room)
        
    if move.time_swap:
        new_time = select_random_time(timeslots, appointment)
        swap_time(case_chain, new_time)
        
   
def make_random_move(schedule: Schedule, compatible_judges_dict: dict[int, list[Judge]], compatible_rooms_dict: dict[int, list[Room]], timeslots: list[int]) -> Schedule:
    """
    Make a random move in the given schedule.
    We make a copy and modify it in place and then return it
    """
    new_schedule = deepcopy(schedule) #TODO avoid deepcopy - do/undo move instead
    chain_dict = identify_appointment_chains(new_schedule)
    
    chosen_case_id: int = select_random_case(list(chain_dict.keys()))
    chosen_case_chain: list[Appointment] = chain_dict[chosen_case_id]
          
    moves = find_all_possible_moves()
    chosen_move: SwapMove = select_random_move(moves)
    
    compatible_judges = compatible_judges_dict[chosen_case_id]
    compatible_rooms = compatible_rooms_dict[chosen_case_id]
    
    process_move(chosen_move, chosen_case_chain, compatible_judges, compatible_rooms, timeslots)
    return new_schedule

def simulated_annealing(schedule: Schedule):
    num_cases = len(schedule.get_all_cases())
    iterations_per_temperature = 30 * (30 - 1) // 2
    start_temperature = 250
    end_temperature = 1
    K = 100
    alpha = calculate_alpha(K, start_temperature, end_temperature)
    
    cases: list[Case]  = schedule.get_all_cases()
    judges: list[Judge] = schedule.get_all_judges()
    rooms: list[Room] = schedule.get_all_rooms() 
    timeslots = schedule.timeslots_per_work_day * schedule.work_days
    
    compatible_judges: dict[int, list[Judge]] = calculate_compatible_judges(cases, judges)
    compatible_rooms: dict[int, list[Room]] = calculate_compatible_rooms(cases, rooms) 
    
    current_schedule = schedule
    best_schedule = deepcopy(schedule)
    current_score = calculate_score(current_schedule)
    best_score = current_score
        
    temperature = start_temperature
    
    for _ in range(K):
        accepted_moves = 0
        
        for _ in range(iterations_per_temperature):
            new_schedule = make_random_move(current_schedule, compatible_judges, compatible_rooms, timeslots)
            new_score = calculate_score(new_schedule)
            
            delta = new_score - current_score
            if delta < 0 or random.random() < math.exp(-delta / temperature):
                current_schedule = new_schedule
                current_score = new_score
                accepted_moves += 1
                
                if current_score < best_score:
                    best_schedule = deepcopy(current_schedule)
                    best_score = current_score
                    if best_score == 0:
                        return best_schedule ## perfect schedule found
                    
        temperature *= alpha
        print(f"Temperature: {temperature:.2f}, Accepted moves: {accepted_moves}, current score: {current_score}, best score: {best_score}")
        
        
        if accepted_moves == 0:
            return best_schedule
        
    
    print_score_summary(best_schedule)
    return best_schedule

def run_local_search(schedule: Schedule) -> Schedule:
    """
    Run the simulated annealing algorithm to improve the given schedule.
    """
    initial_score = calculate_score(schedule)
    print(f"Initial score: {initial_score}")
    
    optimized_schedule = simulated_annealing(schedule)
    
    final_score = calculate_score(optimized_schedule)
    
    visualize(optimized_schedule)
    print(f"Final score: {final_score}")
    return optimized_schedule
    
    
  
    
    
    
    
    

    
    