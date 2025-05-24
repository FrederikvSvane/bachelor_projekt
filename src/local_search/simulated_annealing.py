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
                        move = generate_compound_move(schedule, compatible_judges, compatible_rooms, p_j, p_r, p_t, p_d, tabu_list, current_score, best_score)
                    else: 
                        # single move
                        move = generate_single_random_move(schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score)
                        
                # MEDIUM TEMP
                elif medium_temp_threshold < current_temperature < high_temp_threshold: 
                    p_do_compound_move = 0.6
                    if random.random() < p_do_compound_move: 
                        # compound move
                        p_j, p_r, p_t, p_d = 0.5, 0.5, 0.5, 0.5
                        move = generate_compound_move(schedule, compatible_judges, compatible_rooms, p_j, p_r, p_t, p_d, tabu_list, current_score, best_score)
                    else: 
                        # single move
                        move = generate_single_random_move(schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score)
                        
                # LOW TEMP
                else: 
                    p_do_compound_move = 0.8
                    if random.random() < p_do_compound_move: 
                        # compound move
                        p_j, p_r, p_t, p_d = 0.5, 0.5, 0.5, 0.5
                        move = generate_compound_move(schedule, compatible_judges, compatible_rooms, p_j, p_r, p_t, p_d, tabu_list, current_score, best_score)
                    else: 
                        # single move
                        move = generate_single_random_move(schedule, compatible_judges, compatible_rooms,   tabu_list, current_score, best_score)
                
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

        #if best_hard == 0:
        #    return best_schedule_snapshot.restore_schedule(schedule)
        

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
            r_r_success, num_inserted = apply_ruin_and_recreate(best_schedule_snapshot.restore_schedule(schedule), compatible_judges, compatible_rooms, current_ruin_percentage, in_parallel=True, log_file=log_file)
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
    max_time_seconds = 60 * 30
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


import os

def run_local_search_benchmark(schedule: Schedule, log_file_path: str = None) -> Schedule:
    """
    Run a benchmark of the local search algorithm with various configurations.
    """
    # Create benchmark_tests directory if it doesn't exist
    benchmark_dir = "benchmark_tests"
    os.makedirs(benchmark_dir, exist_ok=True)
    
    iterations_per_temperature = [1000, 2000, 3000, 4000, 5000]
    max_time_seconds = 60 * 5
    start_temps = [200, 300, 400, 500, 600]
    end_temps = [1, 10, 20, 30, 40]
    results = []
    
    total_combinations = len(iterations_per_temperature) * len(start_temps) * len(end_temps)
    current_combination = 0
    
    # Create a summary log file for the entire benchmark
    summary_log_path = os.path.join(benchmark_dir, f"benchmark_summary_{int(time.time())}.log")
    
    print("Running local search benchmark with the following configurations:")
    print(f"Iterations per temperature: {iterations_per_temperature}")
    print(f"Max time: {max_time_seconds} seconds")
    print(f"Start temperatures: {start_temps}")
    print(f"End temperatures: {end_temps}")
    print(f"Total combinations to test: {total_combinations}")
    print(f"Logs will be saved to: {benchmark_dir}/")
    print(f"Summary log: {summary_log_path}")
    print("=" * 80)
    
    # Open summary log file
    with open(summary_log_path, 'w') as summary_log:
        summary_log.write("BENCHMARK CONFIGURATION:\n")
        summary_log.write(f"Iterations per temperature: {iterations_per_temperature}\n")
        summary_log.write(f"Max time: {max_time_seconds} seconds\n")
        summary_log.write(f"Start temperatures: {start_temps}\n")
        summary_log.write(f"End temperatures: {end_temps}\n")
        summary_log.write(f"Total combinations: {total_combinations}\n")
        summary_log.write("=" * 80 + "\n\n")
        
        for iters in iterations_per_temperature:
            for start_temp in start_temps:
                for end_temp in end_temps:
                    current_combination += 1
                    print(f"[{current_combination}/{total_combinations}] Running with iters={iters}, start_temp={start_temp}, end_temp={end_temp}...")
                    
                    # Create individual log file in benchmark_tests directory
                    log_filename = f"local_search_benchmark_{iters}_{start_temp}_{end_temp}.log"
                    log_file_path = os.path.join(benchmark_dir, log_filename)
                    
                    # Log to summary file
                    summary_log.write(f"[{current_combination}/{total_combinations}] Configuration: iters={iters}, start_temp={start_temp}, end_temp={end_temp}\n")
                    summary_log.write(f"Individual log file: {log_filename}\n")
                    summary_log.flush()
                    
                    # Run the simulation
                    start_time = time.time()
                    optimized_schedule = simulated_annealing(
                        schedule,
                        iters,
                        max_time_seconds,
                        start_temp,
                        end_temp,
                        log_file_path=log_file_path
                    )
                    end_time = time.time()
                    
                    final_score = calculate_full_score(optimized_schedule)[0]
                    runtime = end_time - start_time
                    
                    results.append((iters, start_temp, end_temp, final_score, optimized_schedule, runtime))
                    
                    print(f"  → Final score: {final_score} (Runtime: {runtime:.1f}s)")
                    
                    # Log result to summary file
                    summary_log.write(f"Final score: {final_score}\n")
                    summary_log.write(f"Runtime: {runtime:.1f} seconds\n")
                    summary_log.write("-" * 40 + "\n")
                    summary_log.flush()
        
        print("\n" + "=" * 80)
        print("BENCHMARK RESULTS SUMMARY:")
        print("=" * 80)
        
        # Sort by final score (best first)
        results.sort(key=lambda x: x[3])
        
        # Write results to summary log
        summary_log.write("\n" + "=" * 80 + "\n")
        summary_log.write("BENCHMARK RESULTS SUMMARY:\n")
        summary_log.write("=" * 80 + "\n\n")
        
        print("\nAll results (sorted by score, best first):")
        print(f"{'Rank':<4} {'Iterations':<10} {'Start Temp':<10} {'End Temp':<8} {'Final Score':<12} {'Runtime':<10}")
        print("-" * 70)
        
        summary_log.write("All results (sorted by score, best first):\n")
        summary_log.write(f"{'Rank':<4} {'Iterations':<10} {'Start Temp':<10} {'End Temp':<8} {'Final Score':<12} {'Runtime':<10}\n")
        summary_log.write("-" * 70 + "\n")
        
        for rank, (iters, start_temp, end_temp, score, _, runtime) in enumerate(results, 1):
            result_line = f"{rank:<4} {iters:<10} {start_temp:<10} {end_temp:<8} {score:<12.2f} {runtime:<10.1f}s"
            print(result_line)
            summary_log.write(result_line + "\n")
        
        # Display best configuration
        best_iters, best_start_temp, best_end_temp, best_score, best_schedule, best_runtime = results[0]
        
        best_config_text = f"""
{("=" * 80)}
🏆 BEST CONFIGURATION FOUND:
{("=" * 80)}
Iterations per temperature: {best_iters}
Start temperature: {best_start_temp}
End temperature: {best_end_temp}
Final score: {best_score:.2f}
Runtime: {best_runtime:.1f} seconds
{("=" * 80)}
"""
        
        print(best_config_text)
        summary_log.write(best_config_text + "\n")
        
        # Optional: Show top 5 configurations
        top5_text = "\nTop 5 configurations:\n"
        print(top5_text.strip())
        summary_log.write(top5_text)
        
        for rank, (iters, start_temp, end_temp, score, _, runtime) in enumerate(results[:5], 1):
            improvement = ""
            if rank > 1:
                score_diff = score - results[0][3]
                improvement = f" (+{score_diff:.2f})"
            
            config_line = f"{rank}. Iters={iters}, Start={start_temp}, End={end_temp} → Score: {score:.2f}{improvement} (Runtime: {runtime:.1f}s)"
            print(config_line)
            summary_log.write(config_line + "\n")
    
    print(f"\nAll benchmark results saved to: {benchmark_dir}/")
    print(f"Summary saved to: {summary_log_path}")
    
    return best_schedule