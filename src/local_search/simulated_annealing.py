import math
import random
import os
import multiprocessing
from copy import deepcopy
from typing import Dict, List
from collections import deque

from src.base_model.schedule import Schedule
from src.base_model.compatibility_checks import calculate_compatible_judges, calculate_compatible_rooms
from src.local_search.move import do_move, undo_move, Move
from src.local_search.move_generator import generate_random_move, generate_list_random_move
from src.local_search.rules_engine import calculate_full_score, calculate_delta_score

def calculate_alpha(K: int, start_temperature: float, end_temperature: float) -> float:
    """
    Calculate the cooling rate alpha for simulated annealing.
    
    Args:
        K: Number of temperature steps
        start_temperature: Starting temperature
        end_temperature: Ending temperature
        
    Returns:
        Alpha cooling rate
    """
    return (end_temperature / start_temperature) ** (1 / (K - 1))

def check_if_move_is_tabu(move: Move, tabu_list: deque) -> bool:
    """
    Checks if a move is in the tabu list
    """
    meeting_id = move.meeting_id

    if move.new_judge is not None:
        potential_tabu_item = (meeting_id, 'judge', move.new_judge.judge_id)
        if potential_tabu_item in tabu_list:
            # print(f"DEBUG: Move blocked by Tabu (Judge): {potential_tabu_item}") # Optional debug
            return True

    if move.new_room is not None:
        potential_tabu_item = (meeting_id, 'room', move.new_room.room_id)
        if potential_tabu_item in tabu_list:
            # print(f"DEBUG: Move blocked by Tabu (Room): {potential_tabu_item}") # Optional debug
            return True

    if move.new_day is not None or move.new_start_timeslot is not None:
        target_day = move.new_day if move.new_day is not None else move.old_day
        target_start_timeslot = move.new_start_timeslot if move.new_start_timeslot is not None else move.old_start_timeslot

        potential_tabu_item = (meeting_id, 'position', target_day, target_start_timeslot)
        if potential_tabu_item in tabu_list:
            # print(f"DEBUG: Move blocked by Tabu (Position): {potential_tabu_item}") # Optional debug
            return True

    return False

def add_move_to_tabu_list(move: Move, tabu_list: deque) -> None:
    """
    Adds the reverse of the accepted move to the tabu list.
    """
    meeting_id = move.meeting_id

    if move.new_judge is not None and move.new_judge.judge_id != move.old_judge.judge_id:
         tabu_item = (meeting_id, 'judge', move.old_judge.judge_id)
         tabu_list.append(tabu_item)
         # print(f"DEBUG: Adding Tabu: {tabu_item}") # Optional debug print

    if move.new_room is not None and move.new_room.room_id != move.old_room.room_id:
         tabu_item = (meeting_id, 'room', move.old_room.room_id)
         tabu_list.append(tabu_item)
         # print(f"DEBUG: Adding Tabu: {tabu_item}") # Optional debug print

    position_changed = (move.new_day is not None and move.new_day != move.old_day) or \
                       (move.new_start_timeslot is not None and move.new_start_timeslot != move.old_start_timeslot)
    if position_changed:
         tabu_item = (meeting_id, 'position', move.old_day, move.old_start_timeslot)
         tabu_list.append(tabu_item)
         # print(f"DEBUG: Adding Tabu: {tabu_item}") # Optional debug print
         

def calculate_moves_in_parallel(pool, schedule: Schedule, moves_with_gen_int: List[tuple[Move, int]]) -> List[tuple[Move, int]]:
    """
    Calculate the delta scores for a list of moves in parallel
    """
    if not moves_with_gen_int:
        return []

    #print(f"Calculating delta scores for {len(moves_with_gen_int)} moves in parallel...")
    actual_moves: List[Move] = [move for move, _ in moves_with_gen_int]

    starmap_args: List[tuple[Schedule, Move]] = [(schedule, move) for move in actual_moves]

    delta_scores: List[int] = pool.starmap(calculate_delta_score, starmap_args)

    results_combined: List[tuple[Move, int]] = list(zip(actual_moves, delta_scores))

    return results_combined
    
    
def find_best_move_parallel(pool, schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score) -> tuple[Move, int]:
    moves: list[(Move, int)] = generate_list_random_move(schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score)
    
    if not moves:
        return None, 0

    results = calculate_moves_in_parallel(pool, schedule, moves)
    results.sort(key=lambda x: x[1])  # Sort by delta score
    
    return results[0]

def find_best_move_sequential(schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score) -> tuple[Move, int]:
    """
    Find the best move by generating random moves and calculating their delta scores.
    """
    moves: list[(Move, int)] = generate_list_random_move(schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score)
    
    if not moves:
        return None, 0

    sequential_results = []

    # Sort moves by delta score
    for move, _ in moves:
        delta_score = calculate_delta_score(schedule, move)
        sequential_results.append((move, delta_score))
        
    sequential_results.sort(key=lambda x: x[1])  # Sort by delta score
    return sequential_results[0]
        
def find_best_move_single(schedule, compatible_judges, compatible_rooms) -> tuple[Move, int]:
    """
    Find the best move by generating random moves and calculating their delta scores.
    """
    move = generate_random_move(schedule, compatible_judges, compatible_rooms)
    
    if move is None:
        return None, 0

    delta_score = calculate_delta_score(schedule, move)
    
    return move, delta_score

def simulated_annealing(schedule: Schedule, n: int, K: int, start_temp: float, end_temp: float) -> Schedule:
    """
    Perform simulated annealing optimization on the given schedule.
    """
    iterations_per_temperature = n * (n - 1) // 2
    alpha = calculate_alpha(K, start_temp, end_temp)

    meetings = schedule.get_all_meetings()
    judges = schedule.get_all_judges()
    rooms = schedule.get_all_rooms() 
    
    compatible_judges = calculate_compatible_judges(meetings, judges)
    compatible_rooms = calculate_compatible_rooms(meetings, rooms)
    
    # Initial full score calculation
    current_score = calculate_full_score(schedule)
    best_score = current_score
    best_schedule = deepcopy(schedule)
    
    tabu_list = deque(maxlen=20)
    
    temperature = start_temp
    total_moves = 0
    accepted_moves = 0
    
    n_cores = os.cpu_count()
    print(f"Using {n_cores} CPU cores for parallel processing")
    

     
    #with multiprocessing.Pool(processes=n_cores) as pool:
    if True:
        for k in range(K):
            iteration_accepted = 0
            
            for i in range(iterations_per_temperature):
                
                #best_move, best_delta = find_best_move_parallel(pool, schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score)
                #best_move, best_delta = find_best_move_sequential(schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score)
                best_move, best_delta = find_best_move_single(schedule, compatible_judges, compatible_rooms)
                
                if best_move is None:
                    continue
                
                do_move(best_move, schedule) # so this actually modifies the schedule in place
                total_moves += 1
                
                # Accept or reject move
                if best_delta < 0 or random.random() < math.exp(-best_delta / temperature):
                    # Accept move
                    #print(f"Accepted move: {best_move} with delta: {best_delta}")
                    current_score += best_delta
                    iteration_accepted += 1
                    accepted_moves += 1
                    add_move_to_tabu_list(best_move, tabu_list)
                    
                    # Update best solution if needed
                    if current_score < best_score:
                        best_score = current_score
                        best_schedule = deepcopy(schedule)
                        
                else:
                    # Reject move - undo it
                    undo_move(best_move, schedule)
            
            temperature *= alpha
            print(f"Iteration {k+1}/{K} - Temp: {temperature:.2f}, "
                f"Accepted: {iteration_accepted}/{iterations_per_temperature}, "
                f"Current: {current_score}, Best: {best_score}")
            
            # Early termination if no progress
            if iteration_accepted == 0:
                print("Early termination: No moves accepted in this iteration")
                break
        
        print(f"Search completed: {total_moves} moves attempted, {accepted_moves} accepted")
    return best_schedule

def run_local_search(schedule: Schedule) -> Schedule:
    # Parameter ranges to test
    start_temperatures = [300]
    end_temperatures = [10]
    iteration_counts = [80]
    
    # Track results
    results = []
    best_score = float('inf')
    best_schedule = None
    best_params = None
    
    total_combinations = len(start_temperatures) * len(end_temperatures) * len(iteration_counts)
    
    print(f"Testing {total_combinations} parameter combinations...\n")
    print(f"{'Start Temp':^10} | {'End Temp':^8} | {'K':^4} | {'Score':^6}")
    print("-" * 35)
    
    # best_schedule = simulated_annealing(
    #     initial_schedule,
    #     iteration_counts[0],
    #     100,  # Number of temperature steps
    #     start_temperatures[0],
    #     end_temperatures[0]
    # )
    
    for start_temp in start_temperatures:
        for end_temp in end_temperatures:
            for n in iteration_counts:
                test_schedule = deepcopy(schedule)
                
                optimized_schedule = simulated_annealing(test_schedule, n, 100, start_temp, end_temp)
                
                score = calculate_full_score(optimized_schedule)
                
                print(f"{start_temp:^10} | {end_temp:^8} | {n:^4} | {score:^6}")
                result = {
                    "start_temp": start_temp,
                    "end_temp": end_temp,
                    "n": n,
                    "score": score,
                    "schedule": optimized_schedule
                }
                results.append(result)
                
                # Update best result if better
                if score < best_score:
                    best_score = score
                    best_schedule = optimized_schedule
                    best_params = (start_temp, end_temp, n)
    
    # Print summary
    print("\n==== PARAMETER TESTING SUMMARY ====")
    print(f"Best score: {best_score}")
    print(f"Best parameters: start_temp={best_params[0]}, end_temp={best_params[1]}, n={best_params[2]}")
    
    return best_schedule