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

random.seed(13062025)

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


def simulated_annealing(schedule: Schedule, iterations_per_temperature: int, max_time_seconds: int = 60 * 60, start_temp: float = 300, end_temp: float = 1, 
                       high_temp_compound_prob: float = 0.2, medium_temp_compound_prob: float = 0.6, low_temp_compound_prob: float = 0.8,
                       high_temp_threshold_pct: float = 0.6, medium_temp_threshold_pct: float = 0.1,
                       K: int = 100,
                       log_file_path: str = None) -> Schedule:
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
    high_temp_threshold = full_temp_range * high_temp_threshold_pct # from 60% to 100% of the temperature range
    medium_temp_threshold = full_temp_range * medium_temp_threshold_pct # from 10% to 60% of the temperature range
    low_temp_threshold = full_temp_range * 0 # bottom 10% of the temperature range 
     
    plateau_count = 0
    cooling_rate = _calculate_cooling_rate(K, start_temp, end_temp)  # Initial cooling rate # K is 100
    
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
    log_output(f"Move probabilities - High: {high_temp_compound_prob}, Medium: {medium_temp_compound_prob}, Low: {low_temp_compound_prob}")
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
                    p_do_compound_move = high_temp_compound_prob  # Use parameter instead of hardcoded 0.2
                    if random.random() < p_do_compound_move: 
                        # compound move
                        p_j, p_r, p_t, p_d = 0.5, 0.5, 0.5, 0.5
                        move = generate_compound_move(schedule, compatible_judges, compatible_rooms, p_j, p_r, p_t, p_d, tabu_list, current_score, best_score)
                    else: 
                        # single move
                        move = generate_single_random_move(schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score)
                        
                # MEDIUM TEMP
                elif medium_temp_threshold < current_temperature < high_temp_threshold: 
                    p_do_compound_move = medium_temp_compound_prob  # Use parameter instead of hardcoded 0.6
                    if random.random() < p_do_compound_move: 
                        # compound move
                        p_j, p_r, p_t, p_d = 0.5, 0.5, 0.5, 0.5
                        move = generate_compound_move(schedule, compatible_judges, compatible_rooms, p_j, p_r, p_t, p_d, tabu_list, current_score, best_score)
                    else: 
                        # single move
                        move = generate_single_random_move(schedule, compatible_judges, compatible_rooms, tabu_list, current_score, best_score)
                        
                # LOW TEMP
                else: 
                    p_do_compound_move = low_temp_compound_prob  # Use parameter instead of hardcoded 0.8
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
    iterations_per_temperature = 4000
    max_time_seconds = 60 * 3
    start_temp = 200
    end_temp = 30
    
    optimized_schedule = simulated_annealing(
        schedule, 
        iterations_per_temperature, 
        max_time_seconds, 
        start_temp, 
        end_temp,
        log_file_path=log_file_path
    )
    
    return optimized_schedule


def run_move_probability_and_threshold_tuning(schedule: Schedule, best_config_params: tuple, num_runs_per_config: int = 3, max_time_seconds: int = 120) -> Schedule:
    """
    Tune both move selection probabilities AND temperature thresholds using systematic grid search.
    Tests all combinations of 5 move probability sets × 5 threshold sets = 25 total configurations.
    """
    import copy
    import statistics
    
    # Create benchmark_tests directory if it doesn't exist
    benchmark_dir = "benchmark_tests"
    os.makedirs(benchmark_dir, exist_ok=True)
    
    # Create separate folder for combined tuning
    tuning_dir = os.path.join(benchmark_dir, "move_prob_and_threshold_tuning")
    os.makedirs(tuning_dir, exist_ok=True)
    
    # Extract best configuration parameters
    best_iters, best_start_temp, best_end_temp = best_config_params
    
    # Define 5 different move probability combinations
    # Format: (high_temp_prob, medium_temp_prob, low_temp_prob, name)
    move_probability_sets = [
        (0.2, 0.6, 0.8, "Baseline"),
        (0.3, 0.5, 0.7, "Balanced"),
        (0.1, 0.6, 0.8, "LowHigh"),
        (0.2, 0.7, 0.8, "MediumHigh"),
        (0.4, 0.6, 0.9, "Progressive"),
        (0.5, 0.7, 0.9, "Aggressive"),
    ]
    
    # Define 5 different temperature threshold combinations  
    # Format: (high_threshold, medium_threshold, name)
    threshold_sets = [
        (0.6, 0.1, "Current"),          # Current baseline
        (0.5, 0.15, "EarlyMedium"),     # Medium kicks in earlier
        (0.7, 0.2, "LateSwitches"),     # Both switch later  
        (0.4, 0.05, "EarlySwitches"),   # Both switch earlier
        (0.8, 0.3, "Conservative"),      # Very conservative switching
        (0.9, 0.4, "VeryConservative"),  # Extremely conservative switching
    ]
    
    # Store the original schedule
    original_schedule = copy.deepcopy(schedule)
    
    # Create summary log file
    summary_log_path = os.path.join(tuning_dir, f"grid_search_tuning_summary_{int(time.time())}.log")
    
    total_configs = len(move_probability_sets) * len(threshold_sets)
    
    print("Running systematic grid search tuning:")
    print(f"Base config: Iters={best_iters}, Start={best_start_temp}, End={best_end_temp}")
    print(f"Move probability sets: {len(move_probability_sets)}")
    print(f"Threshold sets: {len(threshold_sets)}")
    print(f"Total configurations: {total_configs}")
    print(f"Runs per configuration: {num_runs_per_config}")
    print(f"Max time per run: {max_time_seconds} seconds")
    print(f"Results will be saved to: {tuning_dir}/")
    print("=" * 90)
    
    all_results = {}
    best_overall_score = float('inf')
    best_overall_schedule = None
    best_overall_config = None
    current_config = 0
    
    with open(summary_log_path, 'w') as summary_log:
        summary_log.write("SYSTEMATIC GRID SEARCH TUNING\n")
        summary_log.write(f"Base configuration: Iters={best_iters}, Start={best_start_temp}, End={best_end_temp}\n")
        summary_log.write(f"Move probability sets: {len(move_probability_sets)}\n")
        summary_log.write(f"Threshold sets: {len(threshold_sets)}\n")
        summary_log.write(f"Total configurations: {total_configs}\n")
        summary_log.write(f"Runs per configuration: {num_runs_per_config}\n")
        summary_log.write(f"Max time per run: {max_time_seconds} seconds\n")
        summary_log.write("=" * 90 + "\n\n")
        
        # Write the parameter sets being tested
        summary_log.write("MOVE PROBABILITY SETS:\n")
        for i, (hp, mp, lp, name) in enumerate(move_probability_sets, 1):
            summary_log.write(f"{i}. {name}: High={hp}, Med={mp}, Low={lp}\n")
        
        summary_log.write("\nTHRESHOLD SETS:\n")
        for i, (ht, mt, name) in enumerate(threshold_sets, 1):
            summary_log.write(f"{i}. {name}: High={ht}, Med={mt}\n")
        summary_log.write("\n" + "=" * 90 + "\n\n")
        
        # Test all combinations
        for prob_idx, (high_prob, med_prob, low_prob, prob_name) in enumerate(move_probability_sets):
            for thresh_idx, (high_thresh, med_thresh, thresh_name) in enumerate(threshold_sets):
                current_config += 1
                config_name = f"{prob_name}_{thresh_name}"
                
                print(f"\n[{current_config}/{total_configs}] Testing {config_name}")
                print(f"  Move Probs: H={high_prob}, M={med_prob}, L={low_prob}")
                print(f"  Thresholds: H={high_thresh}, M={med_thresh}")
                print("-" * 70)
                
                summary_log.write(f"CONFIGURATION {current_config}: {config_name}\n")
                summary_log.write(f"Move Probabilities: High={high_prob}, Med={med_prob}, Low={low_prob}\n")
                summary_log.write(f"Temperature Thresholds: High={high_thresh}, Med={med_thresh}\n")
                summary_log.write("-" * 70 + "\n")
                
                config_results = []
                config_runtimes = []
                
                # Create subdirectory for this configuration's runs
                config_dir = os.path.join(tuning_dir, config_name)
                os.makedirs(config_dir, exist_ok=True)
                
                for run in range(1, num_runs_per_config + 1):
                    print(f"  Run {run}/{num_runs_per_config}...", end="", flush=True)
                    
                    # Create fresh copy for this run
                    test_schedule = copy.deepcopy(original_schedule)
                    
                    # Individual run log
                    run_log_path = os.path.join(config_dir, f"run_{run}.log")
                    
                    # Run simulated annealing with this combination
                    start_time = time.time()
                    optimized_schedule = simulated_annealing(
                        test_schedule,
                        best_iters,
                        max_time_seconds,
                        best_start_temp,
                        best_end_temp,
                        high_temp_compound_prob=high_prob,
                        medium_temp_compound_prob=med_prob,
                        low_temp_compound_prob=low_prob,
                        high_temp_threshold_pct=high_thresh,
                        medium_temp_threshold_pct=med_thresh,
                        log_file_path=run_log_path
                    )
                    end_time = time.time()
                    
                    final_score = calculate_full_score(optimized_schedule)[0]
                    runtime = end_time - start_time
                    
                    config_results.append(final_score)
                    config_runtimes.append(runtime)
                    
                    print(f" Score: {final_score:.0f} ({runtime:.1f}s)")
                    
                    summary_log.write(f"Run {run}: Score={final_score:.0f}, Runtime={runtime:.1f}s\n")
                    
                    # Track best overall
                    if final_score < best_overall_score:
                        best_overall_score = final_score
                        best_overall_schedule = copy.deepcopy(optimized_schedule)
                        best_overall_config = f"{config_name}_run{run}"
                
                # Calculate statistics
                mean_score = statistics.mean(config_results)
                std_score = statistics.stdev(config_results) if len(config_results) > 1 else 0
                min_score = min(config_results)
                max_score = max(config_results)
                mean_runtime = statistics.mean(config_runtimes)
                
                all_results[config_name] = {
                    'move_probs': (high_prob, med_prob, low_prob),
                    'thresholds': (high_thresh, med_thresh),
                    'prob_name': prob_name,
                    'thresh_name': thresh_name,
                    'scores': config_results,
                    'mean_score': mean_score,
                    'std_score': std_score,
                    'min_score': min_score,
                    'max_score': max_score,
                    'mean_runtime': mean_runtime
                }
                
                print(f"  → Mean: {mean_score:.0f} ± {std_score:.0f}")
                print(f"  → Best: {min_score:.0f}")
                
                summary_log.write(f"Statistics: Mean={mean_score:.0f}, Std={std_score:.0f}, Min={min_score:.0f}, Max={max_score:.0f}\n")
                summary_log.write(f"Average Runtime: {mean_runtime:.1f}s\n\n")
        
        # Final comparison
        print("\n" + "=" * 100)
        print("GRID SEARCH RESULTS:")
        print("=" * 100)
        
        # Sort by mean score
        sorted_results = sorted(all_results.items(), key=lambda x: x[1]['mean_score'])
        
        print(f"{'Rank':<4} {'Configuration':<20} {'Move Set':<12} {'Thresh Set':<12} {'Mean Score':<12} {'±Std':<10} {'Best':<10}")
        print("-" * 100)
        
        summary_log.write("=" * 100 + "\n")
        summary_log.write("FINAL RESULTS RANKING:\n")
        summary_log.write("=" * 100 + "\n")
        summary_log.write(f"{'Rank':<4} {'Configuration':<20} {'Move Set':<12} {'Thresh Set':<12} {'Mean Score':<12} {'±Std':<10} {'Best':<10}\n")
        summary_log.write("-" * 100 + "\n")
        
        for rank, (config_name, results) in enumerate(sorted_results, 1):
            result_line = f"{rank:<4} {config_name:<20} {results['prob_name']:<12} {results['thresh_name']:<12} {results['mean_score']:<12.0f} ±{results['std_score']:<9.0f} {results['min_score']:<10.0f}"
            print(result_line)
            summary_log.write(result_line + "\n")
        
        # Winner analysis
        winner_name, winner_results = sorted_results[0]
        winner_high_p, winner_med_p, winner_low_p = winner_results['move_probs']
        winner_high_t, winner_med_t = winner_results['thresholds']
        
        winner_text = f"""
{("=" * 100)}
🏆 BEST GRID SEARCH CONFIGURATION:
{("=" * 100)}
Configuration: {winner_name}
Move Probability Set: {winner_results['prob_name']}
Threshold Set: {winner_results['thresh_name']}

DETAILED SETTINGS:
Move Probabilities: High={winner_high_p}, Med={winner_med_p}, Low={winner_low_p}
Temperature Thresholds: High={winner_high_t}, Med={winner_med_t}

PERFORMANCE:
Mean Score: {winner_results['mean_score']:.0f} ± {winner_results['std_score']:.0f}
Best Run: {winner_results['min_score']:.0f}
Consistency: {winner_results['std_score']/winner_results['mean_score']*100:.2f}% variation
Average Runtime: {winner_results['mean_runtime']:.1f} seconds

ANALYSIS BY COMPONENT:
"""
        
        # Analyze which move probability set and threshold set work best overall
        prob_performance = {}
        thresh_performance = {}
        
        for config_name, results in all_results.items():
            prob_name = results['prob_name']
            thresh_name = results['thresh_name']
            score = results['mean_score']
            
            if prob_name not in prob_performance:
                prob_performance[prob_name] = []
            prob_performance[prob_name].append(score)
            
            if thresh_name not in thresh_performance:
                thresh_performance[thresh_name] = []
            thresh_performance[thresh_name].append(score)
        
        winner_text += "Best Move Probability Sets (by average performance):\n"
        prob_avg = [(name, statistics.mean(scores)) for name, scores in prob_performance.items()]
        prob_avg.sort(key=lambda x: x[1])
        for i, (name, avg_score) in enumerate(prob_avg, 1):
            winner_text += f"{i}. {name}: {avg_score:.0f} average\n"
        
        winner_text += "\nBest Threshold Sets (by average performance):\n"
        thresh_avg = [(name, statistics.mean(scores)) for name, scores in thresh_performance.items()]
        thresh_avg.sort(key=lambda x: x[1])
        for i, (name, avg_score) in enumerate(thresh_avg, 1):
            winner_text += f"{i}. {name}: {avg_score:.0f} average\n"
        
        winner_text += f"\n{('=' * 100)}\n"
        
        print(winner_text)
        summary_log.write(winner_text + "\n")
    
    print(f"\nGrid search results saved to: {tuning_dir}/")
    print(f"Summary: {summary_log_path}")
    
    return best_overall_schedule