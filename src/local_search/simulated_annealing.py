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


def simulated_annealing(schedule: Schedule, iterations_per_temperature: int, max_time_seconds: float = float('inf'), start_temp: float = 300, end_temp: float = 1, 
                       high_temp_compound_prob: float = 0.2, medium_temp_compound_prob: float = 0.7, low_temp_compound_prob: float = 0.8,
                       high_temp_threshold_pct: float = 0.5, medium_temp_threshold_pct: float = 0.15,
                       plateau_count_min: int = 6, plateau_count_max: int = 18,
                       ruin_percentage_min: float = 0.002, ruin_percentage_max: float = 0.015,
                       K: int = 75,
                       tabu_tenure: int = 20,
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
    initial_score = [current_score, hard_violations, medium_violations, soft_violations]
    best_score = current_score
    current_temperature = start_temp
    best_schedule_snapshot = ScheduleSnapshot(schedule)

    hard_weight, medium_weight, soft_weight = _calculate_constraint_weights(schedule)
    
    full_temp_range = start_temp - end_temp
    high_temp_threshold = full_temp_range * high_temp_threshold_pct # from 50% to 100% of the temperature range
    medium_temp_threshold = full_temp_range * medium_temp_threshold_pct # from 15% to 50% of the temperature range
    low_temp_threshold = full_temp_range * 0 # bottom 10% of the temperature range 
     
    plateau_count = 0
    cooling_rate = _calculate_cooling_rate(K, start_temp, end_temp)  # Initial cooling rate # K is 100
    
    tabu_list = deque(maxlen=tabu_tenure)
    time_used = 0
    current_iteration = 0
    p_attempt_insert = 0.1
    #plateau_count_min, plateau_count_max = 3, 10
    #ruin_percentage_min, ruin_percentage_max = 0.01, 0.05
    
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

        #if hard_violations == 0:
        #    log_output(f"Iteration: {current_iteration}, Time: {time_used:.1f}s/{max_time_seconds}s, Temp: {current_temperature:.2f}, "
        #      f"Accepted: {moves_accepted_this_iteration}/{moves_explored_this_iteration}, Score: {current_score}, Best: {best_score}, "
        #      f"(Hard: {hard_violations}, Medium: {medium_violations}, Soft: {soft_violations}), "
        #      f"{' - Plateau detected!' if plateau_count >= 3 else ''}")
        #    log_output("All hard violations resolved!")
        #    log_output(f"Days: {schedule.work_days}, Total meetings: {len(schedule.get_all_planned_meetings())}")
        #    return best_schedule_snapshot.restore_schedule(schedule)  # Stop if no hard violations

        # if medium_violations == 0:
        #     visualize(best_schedule_snapshot)

        # if hard_violations == 0 and medium_violations == 0 and soft_violations == 0:
        #     # log_output(f"Iteration: {current_iteration}, Time: {time_used:.1f}s/{max_time_seconds}s, Temp: {current_temperature:.2f}, "
        #     #   f"Accepted: {moves_accepted_this_iteration}/{moves_explored_this_iteration}, Score: {current_score}, Best: {best_score}, "
        #     #   f"(Hard: {hard_violations}, Medium: {medium_violations}, Soft: {soft_violations}), "
        #     #   f"{' - Plateau detected!' if plateau_count >= 3 else ''}")
        #     # log_output("All violations resolved!")
        #     # log_output(f"Days: {schedule.work_days}, Total meetings: {len(schedule.get_all_planned_meetings())}")
        #     return best_schedule_snapshot#.restore_schedule(schedule)
        
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

        if time_used >= max_time_seconds:
            log_output(f"Initial score {initial_score}")
            log_output(f"Final score [{current_score}, {hard_violations}, {medium_violations}, {soft_violations}]")
            log_output(f"Days: {schedule.work_days}, Total meetings: {len(schedule.get_all_planned_meetings())}")

        
        if plateau_count >= current_plateau_limit:
            r_r_success, num_inserted = apply_ruin_and_recreate(best_schedule_snapshot.restore_schedule(schedule), compatible_judges, compatible_rooms, current_ruin_percentage, in_parallel=True)
            plateau_count = 0
            if r_r_success:
                log_output(f"Ruin and Recreate successful! {num_inserted} meetings inserted.\n \n")
                current_score = calculate_full_score(best_schedule_snapshot.restore_schedule(schedule))[0]
                tabu_list.clear()

                if current_score < best_score:
                    best_score = current_score
                    best_schedule_snapshot = ScheduleSnapshot(schedule)
                    log_output(f"New best score found after R&R: {best_score}")
    
    # Close log file if it was opened
    if log_file:
        log_file.close()
                    
    return best_schedule_snapshot.restore_schedule(schedule)

def run_local_search(schedule: Schedule, log_file_path: str = None, K: int = 75) -> Schedule:
    iterations_per_temperature = 4000
    max_time_seconds = 120
    start_temp = 500
    end_temp = 20
    
    optimized_schedule = simulated_annealing(
        schedule, 
        iterations_per_temperature=iterations_per_temperature, 
        max_time_seconds=max_time_seconds, 
        start_temp=start_temp, 
        end_temp=end_temp,
        K=K,
        log_file_path=log_file_path
    )
    
    return optimized_schedule


def run_tabu_tenure_benchmark(base_hyperparams: dict, num_runs_per_tenure: int = 1) -> None:
    """
    Benchmark different tabu tenure values to find the optimal setting.
    base_hyperparams should contain all your other tuned parameters except tabu_tenure.
    """
    import copy
    import statistics
    from src.util.data_generator import generate_test_data_parsed
    
    # Tabu tenure values to test
    tenure_values = [10, 30, 50]
    
    # Fixed problem size for consistent comparison
    n_cases = 1000
    n_days = 60
    test_name = f"TabuTenure_{n_cases}cases_{n_days}days"
    
    # Create results directory
    results_dir = f"benchmark_tests/tabu_tenure_test2"
    os.makedirs(results_dir, exist_ok=True)
    
    # Summary log
    summary_log_path = os.path.join(results_dir, f"tabu_tenure_benchmark_{int(time.time())}.log")
    
    print("TABU TENURE BENCHMARK")
    print("=" * 80)
    print("Testing different tabu tenure values:")
    print(f"Problem size: {n_cases} cases, {n_days} days")
    print(f"Tenure values: {tenure_values}")
    print(f"Runs per tenure: {num_runs_per_tenure}")
    print(f"Total tests: {len(tenure_values) * num_runs_per_tenure}")
    print(f"Results will be saved to: {results_dir}/")
    
    print("\nBase Hyperparameters (excluding tabu_tenure):")
    for param, value in base_hyperparams.items():
        if param != 'tabu_tenure':
            print(f"  {param}: {value}")
    print("=" * 80)
    
    all_results = {}
    
    with open(summary_log_path, 'w') as summary_log:
        summary_log.write("TABU TENURE BENCHMARK\n")
        summary_log.write("=" * 80 + "\n")
        summary_log.write(f"Problem size: {n_cases} cases, {n_days} days\n")
        summary_log.write(f"Runs per tenure: {num_runs_per_tenure}\n")
        summary_log.write("Base Hyperparameters:\n")
        for param, value in base_hyperparams.items():
            if param != 'tabu_tenure':
                summary_log.write(f"  {param}: {value}\n")
        summary_log.write("=" * 80 + "\n\n")
        
        for tenure_idx, tenure_value in enumerate(tenure_values, 1):
            print(f"\n[{tenure_idx}/{len(tenure_values)}] Testing Tabu Tenure: {tenure_value}")
            print("-" * 70)
            
            summary_log.write(f"TENURE TEST {tenure_idx}: {tenure_value}\n")
            summary_log.write("-" * 50 + "\n")
            
            tenure_results = []
            tenure_runtimes = []
            tenure_initial_scores = []
            tenure_improvements = []
            tenure_moves_accepted = []
            
            # Create directory for this tenure value
            tenure_dir = os.path.join(results_dir, f"tenure_{tenure_value}")
            os.makedirs(tenure_dir, exist_ok=True)
            
            for run in range(1, num_runs_per_tenure + 1):
                print(f"  Run {run}/{num_runs_per_tenure}...", end="", flush=True)
                
                # Generate fresh test data for this run (same seed for fair comparison)
                random.seed(13062025 + run)  # Consistent seed per run across all tenures
                parsed_data = generate_test_data_parsed(n_cases, n_days, granularity=5, min_per_work_day=390)
                
                # Initialize compatibility matrices
                from src.base_model.compatibility_checks import initialize_compatibility_matricies
                initialize_compatibility_matricies(parsed_data)

                from src.construction.heuristic.linear_assignment import generate_schedule
                initial_schedule = generate_schedule(parsed_data)
                
                # Initialize and trim schedule
                initial_schedule.initialize_appointment_chains()
                initial_schedule.trim_schedule_length_if_possible()
                
                # Calculate initial score
                initial_score = calculate_full_score(initial_schedule)[0]
                tenure_initial_scores.append(initial_score)
                
                # Individual run log
                run_log_path = os.path.join(tenure_dir, f"run_{run}.log")
                
                # Run simulated annealing with current tenure value
                start_time = time.time()
                optimized_schedule = simulated_annealing(
                    initial_schedule,
                    iterations_per_temperature=base_hyperparams.get('iterations', 4000),
                    max_time_seconds=base_hyperparams.get('max_time', 120),  # Shorter for benchmark
                    start_temp=base_hyperparams.get('start_temp', 500),
                    end_temp=base_hyperparams.get('end_temp', 20),
                    high_temp_compound_prob=base_hyperparams.get('high_prob', 0.2),
                    medium_temp_compound_prob=base_hyperparams.get('med_prob', 0.7),
                    low_temp_compound_prob=base_hyperparams.get('low_prob', 0.8),
                    high_temp_threshold_pct=base_hyperparams.get('high_threshold', 0.5),
                    medium_temp_threshold_pct=base_hyperparams.get('med_threshold', 0.15),
                    plateau_count_min=base_hyperparams.get('plateau_min', 6),
                    plateau_count_max=base_hyperparams.get('plateau_max', 18),
                    ruin_percentage_min=base_hyperparams.get('ruin_min', 0.002),
                    ruin_percentage_max=base_hyperparams.get('ruin_max', 0.015),
                    K=base_hyperparams.get('K', 75),
                    tabu_tenure=tenure_value,  # This is what we're testing!
                    log_file_path=run_log_path
                )
                end_time = time.time()
                
                final_score = calculate_full_score(optimized_schedule)[0]
                runtime = end_time - start_time
                improvement = initial_score - final_score
                improvement_pct = (improvement / initial_score) * 100
                
                tenure_results.append(final_score)
                tenure_runtimes.append(runtime)
                tenure_improvements.append(improvement)
                
                print(f" Initial: {initial_score:.0f} → Final: {final_score:.0f} "
                      f"(↓{improvement:.0f}, {improvement_pct:.1f}%, {runtime:.1f}s)")
                
                summary_log.write(f"Run {run}: Initial={initial_score:.0f}, Final={final_score:.0f}, "
                                f"Improvement={improvement:.0f} ({improvement_pct:.1f}%), Runtime={runtime:.1f}s\n")
            
            # Calculate statistics for this tenure value
            mean_final = statistics.mean(tenure_results)
            std_final = statistics.stdev(tenure_results) if len(tenure_results) > 1 else 0
            mean_initial = statistics.mean(tenure_initial_scores)
            mean_improvement = statistics.mean(tenure_improvements)
            mean_improvement_pct = (mean_improvement / mean_initial) * 100
            mean_runtime = statistics.mean(tenure_runtimes)
            best_final = min(tenure_results)
            worst_final = max(tenure_results)
            
            all_results[tenure_value] = {
                'tenure': tenure_value,
                'mean_initial': mean_initial,
                'mean_final': mean_final,
                'std_final': std_final,
                'best_final': best_final,
                'worst_final': worst_final,
                'mean_improvement': mean_improvement,
                'mean_improvement_pct': mean_improvement_pct,
                'mean_runtime': mean_runtime,
                'all_finals': tenure_results,
                'all_improvements': tenure_improvements
            }
            
            print(f"\n  📊 Tenure {tenure_value} Summary:")
            print(f"    Mean Initial Score: {mean_initial:.0f}")
            print(f"    Mean Final Score: {mean_final:.0f} ± {std_final:.0f}")
            print(f"    Mean Improvement: {mean_improvement:.0f} ({mean_improvement_pct:.1f}%)")
            print(f"    Best Run: {best_final:.0f}")
            print(f"    Worst Run: {worst_final:.0f}")
            print(f"    Average Runtime: {mean_runtime:.1f}s")
            
            summary_log.write(f"\nTenure Summary: Mean Initial={mean_initial:.0f}, Mean Final={mean_final:.0f}±{std_final:.0f}\n")
            summary_log.write(f"Mean Improvement: {mean_improvement:.0f} ({mean_improvement_pct:.1f}%), Runtime: {mean_runtime:.1f}s\n")
            summary_log.write(f"Best: {best_final:.0f}, Worst: {worst_final:.0f}\n\n")
        
        # Final comparison and analysis
        print("\n" + "=" * 80)
        print("TABU TENURE BENCHMARK RESULTS:")
        print("=" * 80)
        
        print(f"{'Tenure':<8} {'Mean Final':<12} {'±Std':<10} {'Best':<8} {'Worst':<8} {'Improvement':<12} {'Runtime':<10}")
        print("-" * 80)
        
        summary_log.write("=" * 80 + "\n")
        summary_log.write("TABU TENURE BENCHMARK RESULTS:\n")
        summary_log.write("=" * 80 + "\n")
        summary_log.write(f"{'Tenure':<8} {'Mean Final':<12} {'±Std':<10} {'Best':<8} {'Worst':<8} {'Improvement':<12} {'Runtime':<10}\n")
        summary_log.write("-" * 80 + "\n")
        
        # Sort by mean final score for easy comparison
        sorted_results = sorted(all_results.items(), key=lambda x: x[1]['mean_final'])
        
        for tenure_value, results in sorted_results:
            result_line = (f"{tenure_value:<8} {results['mean_final']:<12.0f} ±{results['std_final']:<9.0f} "
                          f"{results['best_final']:<8.0f} {results['worst_final']:<8.0f} "
                          f"{results['mean_improvement_pct']:<12.1f}% {results['mean_runtime']:<10.1f}s")
            print(result_line)
            summary_log.write(result_line + "\n")
        
        # Find best performing tenure
        best_tenure = sorted_results[0][0]
        best_results = sorted_results[0][1]
        
        # Analysis
        analysis = f"""
{("=" * 80)}
📈 TABU TENURE ANALYSIS:
{("=" * 80)}

BEST PERFORMING TENURE: {best_tenure}
  Mean Final Score: {best_results['mean_final']:.0f} ± {best_results['std_final']:.0f}
  Mean Improvement: {best_results['mean_improvement_pct']:.1f}%
  Average Runtime: {best_results['mean_runtime']:.1f}s

TENURE INSIGHTS:
"""
        
        # Performance trend analysis
        tenure_vs_performance = [(t, r['mean_final']) for t, r in all_results.items()]
        tenure_vs_performance.sort()
        
        low_tenures = [r for t, r in tenure_vs_performance if t <= 20]
        high_tenures = [r for t, r in tenure_vs_performance if t >= 30]
        
        if low_tenures and high_tenures:
            avg_low = statistics.mean(low_tenures)
            avg_high = statistics.mean(high_tenures)
            
            if avg_low < avg_high:
                analysis += f"  Lower tenure values (≤20) perform better on average: {avg_low:.0f} vs {avg_high:.0f}\n"
            else:
                analysis += f"  Higher tenure values (≥30) perform better on average: {avg_high:.0f} vs {avg_low:.0f}\n"
        
        # Standard deviation analysis
        most_consistent = min(all_results.items(), key=lambda x: x[1]['std_final'])
        least_consistent = max(all_results.items(), key=lambda x: x[1]['std_final'])
        
        analysis += f"  Most consistent: Tenure {most_consistent[0]} (±{most_consistent[1]['std_final']:.0f})\n"
        analysis += f"  Least consistent: Tenure {least_consistent[0]} (±{least_consistent[1]['std_final']:.0f})\n"
        
        # Runtime analysis
        fastest = min(all_results.items(), key=lambda x: x[1]['mean_runtime'])
        slowest = max(all_results.items(), key=lambda x: x[1]['mean_runtime'])
        
        analysis += f"  Fastest: Tenure {fastest[0]} ({fastest[1]['mean_runtime']:.1f}s avg)\n"
        analysis += f"  Slowest: Tenure {slowest[0]} ({slowest[1]['mean_runtime']:.1f}s avg)\n"
        
        analysis += f"""
RECOMMENDATION:
  Use tabu_tenure = {best_tenure} for optimal performance
  This provides the best balance of solution quality and consistency.

{("=" * 80)}
"""
        
        print(analysis)
        summary_log.write(analysis + "\n")
    
    print(f"\nTabu tenure benchmark results saved to: {results_dir}/")
    print(f"Summary: {summary_log_path}")


def run_tabu_tenure_test():
    """Run the tabu tenure benchmark with your current best hyperparameters."""
    
    # Base hyperparameters (excluding tabu_tenure which we're testing)
    base_hyperparams = {
        'iterations': 4000,
        'max_time': 20,        # Shorter for benchmark
        'start_temp': 500,
        'end_temp': 20,
        'high_prob': 0.2,
        'med_prob': 0.7,
        'low_prob': 0.8,
        'high_threshold': 0.5,
        'med_threshold': 0.15,
        'K': 75,
        'plateau_min': 6,
        'plateau_max': 18,
        'ruin_min': 0.002,
        'ruin_max': 0.015,
    }
    
    run_tabu_tenure_benchmark(base_hyperparams, num_runs_per_tenure=1)

