import math
import random
import os
import multiprocessing
from copy import deepcopy
from typing import Dict, List
from collections import deque

from src.base_model.schedule import Schedule
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.compatibility_checks import calculate_compatible_judges, calculate_compatible_rooms
from src.local_search.move import do_move, undo_move, Move
from src.local_search.move_generator import generate_single_move, generate_list_random_move, generate_compound_move, generate_delete_move
from src.local_search.rules_engine import calculate_full_score, calculate_delta_score

def _check_if_move_is_tabu(move: Move, tabu_list: deque) -> bool:
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

def _add_move_to_tabu_list(move: Move, tabu_list: deque) -> None:
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
         

def _calculate_moves_in_parallel(pool, schedule: Schedule, moves_with_gen_int: List[tuple[Move, int]]) -> List[tuple[Move, int]]:
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
    
    
def _find_best_move_parallel(pool, schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score) -> tuple[Move, int]:
    n_cores = os.cpu_count()
    print(f"Using {n_cores} CPU cores for parallel processing")
    moves: list[(Move, int)] = generate_list_random_move(schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score)
    
    if not moves:
        return None, 0

    results = _calculate_moves_in_parallel(pool, schedule, moves)
    results.sort(key=lambda x: x[1])  # Sort by delta score
    
    return results[0]

def _find_best_move_sequential(schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score) -> tuple[Move, int]:
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
        
def _find_move_and_delta(schedule: Schedule, compatible_judges: list[Judge], compatible_rooms: list[Room]) -> tuple[Move, int]:
    """
    Generate a move and calculate its delta score.
    """
    move = generate_single_move(schedule, compatible_judges, compatible_rooms)
    
    if move is None:
        return None, 0

    delta_score = calculate_delta_score(schedule, move)
    
    return move, delta_score

def _calculate_cooling_rate(K: int, start_temperature: float, end_temperature: float) -> float:
    """
    Calculate the cooling rate alpha for simulated annealing.
    
    Args:
        K: Number of temperature steps
        start_temperature: Starting temperature
        end_temperature: Ending temperature
    """
    return (end_temperature / start_temperature) ** (1 / (K - 1))


def simulated_annealing(schedule: Schedule, iterations_per_temperature: int, total_outer_iterations: int, start_temp: float, end_temp: float) -> Schedule:
    cooling_rate = _calculate_cooling_rate(total_outer_iterations, start_temp, end_temp)

    meetings = schedule.get_all_meetings()
    judges = schedule.get_all_judges()
    rooms = schedule.get_all_rooms() 
    
    compatible_judges = calculate_compatible_judges(meetings, judges)
    compatible_rooms = calculate_compatible_rooms(meetings, rooms)
    
    current_score = calculate_full_score(schedule)
    best_score = current_score
    current_temperature = start_temp
    best_schedule = deepcopy(schedule)
    
    full_temp_range = start_temp - end_temp
    high_temp_threshold = full_temp_range * 0.6 # from 60% to 100% of the temperature range
    medium_temp_threshold = full_temp_range * 0.1 # from 10% to 60% of the temperature range
    low_temp_threshold = full_temp_range * 0 # bottom 10% of the temperature range 
    
    plateau_count = 0
    
    tabu_list = deque(maxlen=20)
    
    #with multiprocessing.Pool(processes=n_cores) as pool:
    if True:
        for k in range(total_outer_iterations):
            moves_explored_this_iteration = 0
            moves_accepted_this_iteration = 0
            best_score_improved_this_iteration = False
            best_score_this_iteration = current_score

            for i in range(iterations_per_temperature):
                
                # HIGH TEMP
                if current_temperature > high_temp_threshold: 
                    p_do_compound_move = 0.2
                    if random.random() < p_do_compound_move: 
                        # compound move
                        p_j, p_r, p_t, p_d = 0.5, 0.5, 0.5, 0.5
                        move = generate_compound_move(schedule, compatible_judges, compatible_rooms, p_j, p_r, p_t, p_d)
                    else: 
                        # single move
                        move = generate_single_move(schedule, compatible_judges, compatible_rooms)
                        
                # MEDIUM TEMP
                elif medium_temp_threshold < current_temperature < high_temp_threshold: 
                    p_do_compound_move = 0.6
                    if random.random() < p_do_compound_move: 
                        # compound move
                        p_j, p_r, p_t, p_d = 0.5, 0.5, 0.5, 0.5
                        move = generate_compound_move(schedule, compatible_judges, compatible_rooms, p_j, p_r, p_t, p_d)
                    else: 
                        # single move
                        move = generate_single_move(schedule, compatible_judges, compatible_rooms)
                        
                # LOW TEMP
                else: 
                    RnR_allowed = True
                    p_do_compound_move = 0.8
                    if random.random() < p_do_compound_move: 
                        # compound move
                        p_j, p_r, p_t, p_d = 0.5, 0.5, 0.5, 0.5
                        move = generate_compound_move(schedule, compatible_judges, compatible_rooms, p_j, p_r, p_t, p_d)
                    else: 
                        # single move
                        move = generate_single_move(schedule, compatible_judges, compatible_rooms)
                    
                delta = calculate_delta_score(schedule, move)
                
                moves_explored_this_iteration += 1
                if move is None:
                    print("No valid moves found, skipping iteration")
                    continue
                
                do_move(move, schedule) 
                
                if delta < 0 or random.random() < math.exp(-delta / current_temperature): # accept move
                    moves_accepted_this_iteration += 1
                    current_score += delta
                    best_score_this_iteration = min(best_score_this_iteration, current_score) # just for printing. remove for performance
                    _add_move_to_tabu_list(move, tabu_list)
                    
                    if current_score < best_score:
                        best_score = current_score
                        best_schedule = deepcopy(schedule)
                        plateau_count = 0
                        best_score_improved_this_iteration = True
                        
                else: # reject move
                    undo_move(move, schedule)
            
            current_temperature *= cooling_rate

            if not best_score_improved_this_iteration:
                plateau_count += 1
                
            if moves_accepted_this_iteration == 0: # no progress in this iteration => consider stopping
                print("No moves accepted for this temperature. Consider terminating.")
                continue
            
            print(f"Iteration {k+1}/{total_outer_iterations} - Temp: {current_temperature:.2f}, "
                f"Accepted: {moves_accepted_this_iteration}/{moves_explored_this_iteration}, "
                f"Current: {best_score_this_iteration}, Best: {best_score}"
                f"{' - Plateau detected!' if plateau_count > 5 else ''}")
                    
    return best_schedule

def run_local_search(schedule: Schedule) -> Schedule:
    iterations_per_temperature = 5000
    total_outer_iterations = 100
    start_temp = 300
    end_temp = 1
    
    optimized_schedule = simulated_annealing(schedule, iterations_per_temperature, total_outer_iterations, start_temp, end_temp)
    
    return optimized_schedule