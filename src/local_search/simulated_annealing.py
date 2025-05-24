import math
import random
import os
import time
import multiprocessing
from copy import deepcopy
from typing import Dict, List
from collections import deque
from src.local_search.ScheduleSnapshot import ScheduleSnapshot

from src.base_model.schedule import Schedule
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.compatibility_checks import calculate_compatible_judges, calculate_compatible_rooms
from src.local_search.move import do_move, undo_move, Move
from src.local_search.move_generator import generate_single_random_move, generate_list_of_random_moves, generate_compound_move, generate_specific_delete_move, generate_random_insert_move, generate_contracting_move
from src.local_search.rules_engine import calculate_full_score, calculate_delta_score
from src.local_search.ruin_and_recreate import apply_ruin_and_recreate
from src.util.schedule_visualizer import visualize
from src.local_search.rules_engine import _calculate_constraint_weights

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
    moves: list[(Move, int)] = generate_list_of_random_moves(schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score)
    
    if not moves:
        return None, 0

    results = _calculate_moves_in_parallel(pool, schedule, moves)
    results.sort(key=lambda x: x[1])  # Sort by delta score
    
    return results[0]

def _find_best_move_sequential(schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score) -> tuple[Move, int]:
    """
    Find the best move by generating random moves and calculating their delta scores.
    """
    moves: list[(Move, int)] = generate_list_of_random_moves(schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score)
    
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
    move = generate_single_random_move(schedule, compatible_judges, compatible_rooms)
    
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
def extract_violations_from_score(score: int, schedule: Schedule, hard_weight, medium_weight, soft_weight) -> tuple[int, int, int]:
    """
    Extract hard, medium and soft violations from a total score based on the weights.
    """
    # Get the weights calculated from the schedule dimensions
    
    # Extract violations by integer division and modulo
    hard_count = score // hard_weight
    medium_count = (score % hard_weight) // medium_weight
    soft_count = (score % medium_weight) // soft_weight
    
    return hard_count, medium_count, soft_count


def simulated_annealing(schedule: Schedule, iterations_per_temperature: int, max_time_seconds: int = 60 * 60, start_temp: float = 300, end_temp: float = 1, log_file_path: str = None) -> Schedule:
    from copy import deepcopy
    start_time = time.time()
    
    # Open log file if path is provided
    log_file = None
    if log_file_path:
        try:
            log_file = open(log_file_path, 'w')
        except Exception as e:
            print(f"Error opening log file: {e}")
    
    # Custom log function to write to both console and file
    def log_output(message):
        print(message)
        if log_file:
            log_file.write(message + "\n")
            log_file.flush()  # Ensure data is written immediately
    
    meetings = schedule.get_all_planned_meetings()
    judges = schedule.get_all_judges()
    rooms = schedule.get_all_rooms() 
    
    compatible_judges = calculate_compatible_judges(meetings, judges)
    compatible_rooms = calculate_compatible_rooms(meetings, rooms)
    

    current_score, hard_violations, medium_violations, soft_violations = calculate_full_score(schedule)
    best_score = current_score
    current_temperature = start_temp
    best_schedule_snapshot = ScheduleSnapshot(schedule)

    hard_weight, medium_weight, soft_weight = _calculate_constraint_weights(schedule)
    
    full_temp_range = start_temp - end_temp
    high_temp_threshold = full_temp_range * 0.6 # from 60% to 100% of the temperature range
    medium_temp_threshold = full_temp_range * 0.1 # from 10% to 60% of the temperature range
    low_temp_threshold = full_temp_range * 0 # bottom 10% of the temperature range 
     
    plateau_count = 0
    cooling_rate = _calculate_cooling_rate(100, start_temp, end_temp)  # Initial cooling rate
    
    tabu_list = deque(maxlen=20)
    time_used = 0
    current_iteration = 0
    p_attempt_insert = 0.1
    plateau_count_min, plateau_count_max = 3, 10
    ruin_percentage_min, ruin_percentage_max = 0.01, 0.05
    
    log_output(f"Starting simulated annealing with parameters:")
    log_output(f"Iterations per temperature: {iterations_per_temperature}")
    log_output(f"Max time: {max_time_seconds} seconds")
    log_output(f"Start temperature: {start_temp}")
    log_output(f"End temperature: {end_temp}")
    log_output(f"Initial score: {current_score}")
    log_output(f"Initial violations - Hard: {hard_violations}, Medium: {medium_violations}, Soft: {soft_violations}")

    while time_used < max_time_seconds:
        time_used = time.time() - start_time
            
        moves_explored_this_iteration = 0
        moves_accepted_this_iteration = 0
        best_score_improved_this_iteration = False
        best_score_this_iteration = current_score
        
        normalized_temp = current_temperature / start_temp
        current_plateau_limit = int(plateau_count_min + (plateau_count_max - plateau_count_min) * (1 - normalized_temp)) # starts low, goes high
        current_ruin_percentage = ruin_percentage_min + (ruin_percentage_max - ruin_percentage_min) * (1 - normalized_temp) # start low, goes high
        
        # Apply contracting move at the start of each outer iteration (temperature change)
        # This is a large, expensive move that should not be in the inner loop
        if current_iteration > 0:  # Skip first iteration to avoid double-contracting initial schedule
            # log_output(f"Applying contracting move at start of iteration {current_iteration + 1}...")
            pre_contract_score = current_score
            
            contracting_move = generate_contracting_move(schedule, debug=False)
            post_contract_score = calculate_full_score(schedule)[0]
            
            # Always accept contracting move if it improves the score
            if post_contract_score < pre_contract_score:
                current_score = post_contract_score
                # log_output(f"Contracting move accepted: {pre_contract_score} -> {post_contract_score} "
                        #   f"(Δ: {post_contract_score - pre_contract_score}, "
                        #   f"moves: {len(contracting_move.individual_moves)}, "
                        #   f"skipped: {len(contracting_move.skipped_meetings)})")
                
                # Update best score if this is a new best
                if current_score < best_score:
                    best_score = current_score
                    best_schedule_snapshot = ScheduleSnapshot(schedule)
                    best_score_improved_this_iteration = True
                    # log_output(f"New best score found from contracting: {best_score}")
                    
            else:
                # Contracting move didn't improve - undo it
                from src.local_search.move import undo_contracting_move
                undo_contracting_move(contracting_move, schedule)
                log_output(f"Contracting move rejected: no improvement "
                          f"(moves: {len(contracting_move.individual_moves)}, "
                          f"skipped: {len(contracting_move.skipped_meetings)})")
        
        for i in range(iterations_per_temperature):
            move = None
            if schedule.unplanned_meetings and random.random() < p_attempt_insert: # After RnR, we risk having unplanned meetings due to the regret based insertion strategy. Therefore we look at the unplanned meetings, and try to generate insert moves if its not empty.
                try:
                    move = generate_random_insert_move(schedule)
                except ValueError: # Handle case where insert move generation fails
                    move = None

            if move is None: # No insert move was generated, so we generate a random single or compound move
                # HIGH TEMP
                if current_temperature > high_temp_threshold: 
                    p_do_compound_move = 0.2
                    if random.random() < p_do_compound_move: 
                        # compound move
                        p_j, p_r, p_t, p_d = 0.5, 0.5, 0.5, 0.5
                        move = generate_compound_move(schedule, compatible_judges, compatible_rooms, p_j, p_r, p_t, p_d)
                    else: 
                        # single move
                        move = generate_single_random_move(schedule, compatible_judges, compatible_rooms)
                        
                # MEDIUM TEMP
                elif medium_temp_threshold < current_temperature < high_temp_threshold: 
                    p_do_compound_move = 0.6
                    if random.random() < p_do_compound_move: 
                        # compound move
                        p_j, p_r, p_t, p_d = 0.5, 0.5, 0.5, 0.5
                        move = generate_compound_move(schedule, compatible_judges, compatible_rooms, p_j, p_r, p_t, p_d)
                    else: 
                        # single move
                        move = generate_single_random_move(schedule, compatible_judges, compatible_rooms)
                        
                # LOW TEMP
                else: 
                    p_do_compound_move = 0.8
                    if random.random() < p_do_compound_move: 
                        # compound move
                        p_j, p_r, p_t, p_d = 0.5, 0.5, 0.5, 0.5
                        move = generate_compound_move(schedule, compatible_judges, compatible_rooms, p_j, p_r, p_t, p_d)
                    else: 
                        # single move
                        move = generate_single_random_move(schedule, compatible_judges, compatible_rooms)
                
            delta = calculate_delta_score(schedule, move)
                
            moves_explored_this_iteration += 1
            if move is None:
                log_output("No valid moves found, skipping iteration")
                continue
            
            do_move(move, schedule) 
            
            if delta < 0 or random.random() < math.exp(-delta / current_temperature): # accept move
                moves_accepted_this_iteration += 1
                current_score += delta
                best_score_this_iteration = min(best_score_this_iteration, current_score) # just for printing. remove for performance
                _add_move_to_tabu_list(move, tabu_list)
                
                if current_score < best_score:
                    best_score = current_score
                    plateau_count = 0
                    best_schedule_snapshot = ScheduleSnapshot(schedule)
                    best_score_improved_this_iteration = True

                    
            else: # reject move
                undo_move(move, schedule)
        
        #Extract the bset_score violations based on score:
        best_hard, best_medium, best_soft = extract_violations_from_score(best_score, schedule, hard_weight, medium_weight, soft_weight)
        hard_violations = best_hard
        medium_violations = best_medium
        soft_violations = best_soft
        

        current_iteration += 1
        current_temperature *= cooling_rate
        
        if not best_score_improved_this_iteration:
            plateau_count += 1
        
        # Reheat if temperature gets too low but we still have time
        if current_temperature < end_temp:
            log_output("Reheating")
            current_temperature = start_temp
        
        # Exit if no progress is being made
        if moves_accepted_this_iteration == 0:
            log_output("No moves accepted for this temperature. Consider terminating.")
            continue
        
        log_output(f"Iteration: {current_iteration}, Time: {time_used:.1f}s/{max_time_seconds}s, Temp: {current_temperature:.2f}, "
              f"Accepted: {moves_accepted_this_iteration}/{moves_explored_this_iteration}, Score: {current_score}, Best: {best_score}, "
              f"(Hard: {hard_violations}, Medium: {medium_violations}, Soft: {soft_violations}), "
              f"{' - Plateau detected!' if plateau_count >= 3 else ''}")

        
        if plateau_count >= current_plateau_limit:
            log_output("\n \n _______________________________________________________________ \n Large plateau detected! Applying Ruin and Recreate... \n _______________________________________________________________ \n")
            r_r_success, num_inserted = apply_ruin_and_recreate(best_schedule_snapshot.restore_schedule(schedule), compatible_judges, compatible_rooms, current_ruin_percentage, in_parallel=True)
            plateau_count = 0
            if r_r_success:
                log_output(f"Ruin and Recreate successful! {num_inserted} meetings inserted.\n \n")
                result = calculate_full_score(best_schedule_snapshot.restore_schedule(schedule))
                current_score = result[0]
                tabu_list.clear()

                if current_score < best_score:
                    best_score = current_score
                    best_schedule_snapshot = ScheduleSnapshot(schedule)
                    log_output(f"New best score found after R&R: {best_score}")
    
    # Close log file if it was opened
    if log_file:
        log_file.close()
                    
    return best_schedule_snapshot.restore_schedule(schedule)

def run_local_search(schedule: Schedule, log_file_path: str = None) -> Schedule:
    iterations_per_temperature = 5000
    max_time_seconds = 60 * 2
    start_temp = 300
    end_temp = 10
    
    optimized_schedule = simulated_annealing(
        schedule, 
        iterations_per_temperature, 
        max_time_seconds, 
        start_temp, 
        end_temp,
        log_file_path=log_file_path
    )
    
    return optimized_schedule