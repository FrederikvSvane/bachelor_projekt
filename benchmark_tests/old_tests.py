def run_local_search_benchmark(schedule: Schedule, log_file_path: str = None) -> Schedule:
    """
    Run a benchmark of the local search algorithm with various configurations.
    """
    # Create benchmark_tests directory if it doesn't exist
    benchmark_dir = "benchmark_tests"
    os.makedirs(benchmark_dir, exist_ok=True)
    
    iterations_per_temperature = [1000, 2000, 3000, 4000, 5000]
    max_time_seconds = 60 * 2
    start_temps = [200, 300, 400, 500, 600]
    end_temps = [1, 10, 20, 30, 40]
    results = []
    
    # Store the original schedule to copy from for each test
    original_schedule = copy.deepcopy(schedule)
    
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
                    
                    # **KEY FIX: Create a fresh copy of the original schedule for each test**
                    test_schedule = copy.deepcopy(original_schedule)
                    
                    # Run the simulation on the fresh copy
                    start_time = time.time()
                    optimized_schedule = simulated_annealing(
                        test_schedule,  # Use the fresh copy instead of the modified schedule
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
        
        # Rest of the function remains the same...
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

def run_focused_benchmark(schedule: Schedule, num_runs_per_config: int = 5, max_time_seconds: int = 180) -> Schedule:
    """
    Run a focused benchmark on the top performing configurations with multiple runs each.
    """
    import copy
    import statistics
    
    # Create benchmark_tests directory if it doesn't exist
    benchmark_dir = "benchmark_tests"
    os.makedirs(benchmark_dir, exist_ok=True)
    
    # Create separate folder for focused benchmark
    focused_dir = os.path.join(benchmark_dir, "focused_benchmark")
    os.makedirs(focused_dir, exist_ok=True)
    
    # Top 5 configurations from previous benchmark
    top_configs = [
        (2000, 200, 20, "Config1_2000_200_20"),
        (4000, 500, 20, "Config2_4000_500_20"), 
        (5000, 500, 10,  "Config3_5000_500_10"),
        (3000, 300, 20, "Config4_3000_300_20"),
        (5000, 400, 40, "Config5_5000_400_40")
    ]
    
    # Store the original schedule
    original_schedule = copy.deepcopy(schedule)
    
    # Create detailed log file in focused directory
    detailed_log_path = os.path.join(focused_dir, f"focused_benchmark_summary_{int(time.time())}.log")
    
    print("Running focused benchmark on top 5 configurations:")
    print(f"Number of runs per configuration: {num_runs_per_config}")
    print(f"Max time per run: {max_time_seconds} seconds")
    print(f"Results will be saved to: {focused_dir}/")
    print("=" * 80)
    
    all_results = {}
    best_overall_score = float('inf')
    best_overall_schedule = None
    best_overall_config = None
    
    with open(detailed_log_path, 'w') as detailed_log:
        detailed_log.write("FOCUSED BENCHMARK - TOP 5 CONFIGURATIONS\n")
        detailed_log.write(f"Runs per configuration: {num_runs_per_config}\n")
        detailed_log.write(f"Max time per run: {max_time_seconds} seconds\n")
        detailed_log.write(f"Results directory: {focused_dir}\n")
        detailed_log.write("=" * 80 + "\n\n")
        
        for config_idx, (iters, start_temp, end_temp, config_name) in enumerate(top_configs, 1):
            print(f"\n[{config_idx}/5] Testing {config_name}: Iters={iters}, Start={start_temp}, End={end_temp}")
            print("-" * 60)
            
            detailed_log.write(f"CONFIGURATION {config_idx}: {config_name}\n")
            detailed_log.write(f"Parameters: Iters={iters}, Start={start_temp}, End={end_temp}\n")
            detailed_log.write("-" * 60 + "\n")
            
            config_results = []
            config_runtimes = []
            
            # Create subdirectory for this configuration's runs
            config_dir = os.path.join(focused_dir, config_name)
            os.makedirs(config_dir, exist_ok=True)
            
            for run in range(1, num_runs_per_config + 1):
                print(f"  Run {run}/{num_runs_per_config}...", end="", flush=True)
                
                # Create fresh copy for this run
                test_schedule = copy.deepcopy(original_schedule)
                
                # Individual run log in config subdirectory
                run_log_path = os.path.join(config_dir, f"run_{run}.log")
                
                # Run the algorithm
                start_time = time.time()
                optimized_schedule = simulated_annealing(
                    test_schedule,
                    iters,
                    max_time_seconds,
                    start_temp,
                    end_temp,
                    log_file_path=run_log_path
                )
                end_time = time.time()
                
                final_score = calculate_full_score(optimized_schedule)[0]
                runtime = end_time - start_time
                
                config_results.append(final_score)
                config_runtimes.append(runtime)
                
                print(f" Score: {final_score:.0f} ({runtime:.1f}s)")
                
                detailed_log.write(f"Run {run}: Score={final_score:.0f}, Runtime={runtime:.1f}s, Log: {run_log_path}\n")
                
                # Track best overall
                if final_score < best_overall_score:
                    best_overall_score = final_score
                    best_overall_schedule = copy.deepcopy(optimized_schedule)
                    best_overall_config = f"{config_name}_run{run}"
            
            # Calculate statistics for this configuration
            mean_score = statistics.mean(config_results)
            std_score = statistics.stdev(config_results) if len(config_results) > 1 else 0
            min_score = min(config_results)
            max_score = max(config_results)
            mean_runtime = statistics.mean(config_runtimes)
            
            all_results[config_name] = {
                'params': (iters, start_temp, end_temp),
                'scores': config_results,
                'runtimes': config_runtimes,
                'mean_score': mean_score,
                'std_score': std_score,
                'min_score': min_score,
                'max_score': max_score,
                'mean_runtime': mean_runtime
            }
            
            print(f"  → Mean: {mean_score:.0f} ± {std_score:.0f}")
            print(f"  → Range: {min_score:.0f} - {max_score:.0f}")
            print(f"  → Avg Runtime: {mean_runtime:.1f}s")
            
            detailed_log.write(f"Statistics: Mean={mean_score:.0f}, Std={std_score:.0f}, Min={min_score:.0f}, Max={max_score:.0f}\n")
            detailed_log.write(f"Average Runtime: {mean_runtime:.1f}s\n")
            detailed_log.write(f"Individual run logs saved in: {config_dir}/\n\n")
    
    # Final comparison
    print("\n" + "=" * 80)
    print("FOCUSED BENCHMARK RESULTS COMPARISON:")
    print("=" * 80)
    
    # Sort configurations by mean score
    sorted_configs = sorted(all_results.items(), key=lambda x: x[1]['mean_score'])
    
    print(f"{'Rank':<4} {'Configuration':<20} {'Mean Score':<15} {'±Std':<12} {'Best':<15} {'Worst':<15} {'Avg Time':<10}")
    print("-" * 100)
    
    with open(detailed_log_path, 'a') as detailed_log:
        detailed_log.write("=" * 80 + "\n")
        detailed_log.write("FINAL COMPARISON RESULTS:\n")
        detailed_log.write("=" * 80 + "\n")
        detailed_log.write(f"{'Rank':<4} {'Configuration':<20} {'Mean Score':<15} {'±Std':<12} {'Best':<15} {'Worst':<15} {'Avg Time':<10}\n")
        detailed_log.write("-" * 100 + "\n")
        
        for rank, (config_name, results) in enumerate(sorted_configs, 1):
            iters, start_temp, end_temp = results['params']
            result_line = f"{rank:<4} {config_name:<20} {results['mean_score']:<15.0f} ±{results['std_score']:<11.0f} {results['min_score']:<15.0f} {results['max_score']:<15.0f} {results['mean_runtime']:<10.1f}s"
            print(result_line)
            detailed_log.write(result_line + "\n")
        
        # Winner details
        winner_name, winner_results = sorted_configs[0]
        winner_text = f"""
{("=" * 80)}
🏆 WINNER: {winner_name}
{("=" * 80)}
Parameters: Iters={winner_results['params'][0]}, Start={winner_results['params'][1]}, End={winner_results['params'][2]}
Mean Score: {winner_results['mean_score']:.0f} ± {winner_results['std_score']:.0f}
Best Run Score: {winner_results['min_score']:.0f}
Consistency: {winner_results['std_score']/winner_results['mean_score']*100:.2f}% variation
Average Runtime: {winner_results['mean_runtime']:.1f} seconds
{("=" * 80)}
"""
        print(winner_text)
        detailed_log.write(winner_text + "\n")
        
        detailed_log.write(f"\nFOLDER STRUCTURE:\n")
        detailed_log.write(f"Main directory: {focused_dir}/\n")
        detailed_log.write(f"Summary log: {detailed_log_path}\n")
        for config_name, _ in sorted_configs:
            detailed_log.write(f"Config logs: {os.path.join(focused_dir, config_name)}/\n")
    
    print(f"\nAll focused benchmark results saved to: {focused_dir}/")
    print(f"Summary log: {detailed_log_path}")
    print(f"\nFolder structure:")
    print(f"├── {focused_dir}/")
    print(f"│   ├── focused_benchmark_summary_[timestamp].log")
    for config_name, _ in sorted_configs:
        print(f"│   ├── {config_name}/")
        for run in range(1, num_runs_per_config + 1):
            print(f"│   │   └── run_{run}.log")
    
    return best_overall_schedule


def run_move_probability_tuning(schedule: Schedule, best_config_params: tuple, num_runs_per_config: int = 3, max_time_seconds: int = 120) -> Schedule:
    """
    Tune the move selection probabilities for different temperature ranges.
    best_config_params should be (iterations, start_temp, end_temp) from your previous best result.
    """
    import copy
    import statistics
    
    # Create benchmark_tests directory if it doesn't exist
    benchmark_dir = "benchmark_tests"
    os.makedirs(benchmark_dir, exist_ok=True)
    
    # Create separate folder for move probability tuning
    tuning_dir = os.path.join(benchmark_dir, "move_probability_tuning")
    os.makedirs(tuning_dir, exist_ok=True)
    
    # Extract best configuration parameters
    best_iters, best_start_temp, best_end_temp = best_config_params
    
    # Define probability combinations to test
    # Format: (high_temp_prob, medium_temp_prob, low_temp_prob, description)
    probability_combinations = [
        # Current baseline
        (0.2, 0.6, 0.8, "Current_Baseline"),
        
        # More exploration at high temp
        (0.4, 0.6, 0.8, "HighExplore_1"),
        (0.5, 0.6, 0.8, "HighExplore_2"),
        
        # Less compound moves at high temp (more single moves for exploration)
        (0.1, 0.6, 0.8, "LowHigh_1"),
        (0.15, 0.6, 0.8, "LowHigh_2"),
        
        # Adjust medium temp
        (0.2, 0.5, 0.8, "MediumLow_1"),
        (0.2, 0.7, 0.8, "MediumHigh_1"),
        
        # Adjust low temp (more fine-tuning)
        (0.2, 0.6, 0.9, "LowHigh_3"),
        (0.2, 0.6, 0.7, "LowLow_1"),
        
        # Balanced approaches
        (0.3, 0.5, 0.7, "Balanced_1"),
        (0.3, 0.6, 0.7, "Balanced_2"),
        
        # Gradual increase
        (0.2, 0.4, 0.6, "Gradual_1"),
        (0.3, 0.5, 0.8, "Gradual_2"),
        
        # Aggressive compound moves
        (0.6, 0.7, 0.9, "Aggressive_1"),
        (0.5, 0.8, 0.9, "Aggressive_2"),
    ]
    
    # Store the original schedule
    original_schedule = copy.deepcopy(schedule)
    
    # Create summary log file
    summary_log_path = os.path.join(tuning_dir, f"move_probability_tuning_summary_{int(time.time())}.log")
    
    print("Running move probability tuning with best configuration:")
    print(f"Base config: Iters={best_iters}, Start={best_start_temp}, End={best_end_temp}")
    print(f"Number of probability combinations: {len(probability_combinations)}")
    print(f"Runs per combination: {num_runs_per_config}")
    print(f"Max time per run: {max_time_seconds} seconds")
    print(f"Results will be saved to: {tuning_dir}/")
    print("=" * 80)
    
    all_results = {}
    best_overall_score = float('inf')
    best_overall_schedule = None
    best_overall_config = None
    
    with open(summary_log_path, 'w') as summary_log:
        summary_log.write("MOVE PROBABILITY TUNING\n")
        summary_log.write(f"Base configuration: Iters={best_iters}, Start={best_start_temp}, End={best_end_temp}\n")
        summary_log.write(f"Probability combinations tested: {len(probability_combinations)}\n")
        summary_log.write(f"Runs per combination: {num_runs_per_config}\n")
        summary_log.write(f"Max time per run: {max_time_seconds} seconds\n")
        summary_log.write("=" * 80 + "\n\n")
        
        for combo_idx, (high_prob, med_prob, low_prob, combo_name) in enumerate(probability_combinations, 1):
            print(f"\n[{combo_idx}/{len(probability_combinations)}] Testing {combo_name}")
            print(f"  High temp: {high_prob} | Medium temp: {med_prob} | Low temp: {low_prob}")
            print("-" * 60)
            
            summary_log.write(f"COMBINATION {combo_idx}: {combo_name}\n")
            summary_log.write(f"Probabilities: High={high_prob}, Medium={med_prob}, Low={low_prob}\n")
            summary_log.write("-" * 60 + "\n")
            
            combo_results = []
            combo_runtimes = []
            
            # Create subdirectory for this combination's runs
            combo_dir = os.path.join(tuning_dir, combo_name)
            os.makedirs(combo_dir, exist_ok=True)
            
            for run in range(1, num_runs_per_config + 1):
                print(f"  Run {run}/{num_runs_per_config}...", end="", flush=True)
                
                # Create fresh copy for this run
                test_schedule = copy.deepcopy(original_schedule)
                
                # Individual run log
                run_log_path = os.path.join(combo_dir, f"run_{run}.log")
                
                # Run simulated annealing with modified probabilities
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
                    log_file_path=run_log_path
                )
                end_time = time.time()
                
                final_score = calculate_full_score(optimized_schedule)[0]
                runtime = end_time - start_time
                
                combo_results.append(final_score)
                combo_runtimes.append(runtime)
                
                print(f" Score: {final_score:.0f} ({runtime:.1f}s)")
                
                summary_log.write(f"Run {run}: Score={final_score:.0f}, Runtime={runtime:.1f}s\n")
                
                # Track best overall
                if final_score < best_overall_score:
                    best_overall_score = final_score
                    best_overall_schedule = copy.deepcopy(optimized_schedule)
                    best_overall_config = f"{combo_name}_run{run}"
            
            # Calculate statistics
            mean_score = statistics.mean(combo_results)
            std_score = statistics.stdev(combo_results) if len(combo_results) > 1 else 0
            min_score = min(combo_results)
            max_score = max(combo_results)
            mean_runtime = statistics.mean(combo_runtimes)
            
            all_results[combo_name] = {
                'probabilities': (high_prob, med_prob, low_prob),
                'scores': combo_results,
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
        print("\n" + "=" * 80)
        print("MOVE PROBABILITY TUNING RESULTS:")
        print("=" * 80)
        
        # Sort by mean score
        sorted_results = sorted(all_results.items(), key=lambda x: x[1]['mean_score'])
        
        print(f"{'Rank':<4} {'Configuration':<18} {'High':<6} {'Med':<6} {'Low':<6} {'Mean Score':<12} {'±Std':<10} {'Best':<12}")
        print("-" * 85)
        
        summary_log.write("=" * 80 + "\n")
        summary_log.write("FINAL RESULTS RANKING:\n")
        summary_log.write("=" * 80 + "\n")
        summary_log.write(f"{'Rank':<4} {'Configuration':<18} {'High':<6} {'Med':<6} {'Low':<6} {'Mean Score':<12} {'±Std':<10} {'Best':<12}\n")
        summary_log.write("-" * 85 + "\n")
        
        for rank, (combo_name, results) in enumerate(sorted_results, 1):
            high_p, med_p, low_p = results['probabilities']
            result_line = f"{rank:<4} {combo_name:<18} {high_p:<6} {med_p:<6} {low_p:<6} {results['mean_score']:<12.0f} ±{results['std_score']:<9.0f} {results['min_score']:<12.0f}"
            print(result_line)
            summary_log.write(result_line + "\n")
        
        # Winner analysis
        winner_name, winner_results = sorted_results[0]
        winner_high, winner_med, winner_low = winner_results['probabilities']
        
        winner_text = f"""
{("=" * 80)}
🏆 BEST MOVE PROBABILITY CONFIGURATION:
{("=" * 80)}
Configuration: {winner_name}
High Temperature Compound Probability: {winner_high} ({winner_high*100:.0f}% compound, {(1-winner_high)*100:.0f}% single)
Medium Temperature Compound Probability: {winner_med} ({winner_med*100:.0f}% compound, {(1-winner_med)*100:.0f}% single)
Low Temperature Compound Probability: {winner_low} ({winner_low*100:.0f}% compound, {(1-winner_low)*100:.0f}% single)

Performance:
Mean Score: {winner_results['mean_score']:.0f} ± {winner_results['std_score']:.0f}
Best Run: {winner_results['min_score']:.0f}
Consistency: {winner_results['std_score']/winner_results['mean_score']*100:.2f}% variation
Average Runtime: {winner_results['mean_runtime']:.1f} seconds

Compared to baseline:
"""
        
        # Compare to baseline if it exists
        if "Current_Baseline" in all_results:
            baseline = all_results["Current_Baseline"]
            improvement = baseline['mean_score'] - winner_results['mean_score']
            winner_text += f"Improvement over baseline: {improvement:.0f} points ({improvement/baseline['mean_score']*100:.2f}%)\n"
        
        winner_text += f"{('=' * 80)}\n"
        
        print(winner_text)
        summary_log.write(winner_text + "\n")
        
        summary_log.write(f"\nFOLDER STRUCTURE:\n")
        summary_log.write(f"Main directory: {tuning_dir}/\n")
        summary_log.write(f"Summary log: {summary_log_path}\n")
        for combo_name, _ in sorted_results:
            summary_log.write(f"Config logs: {os.path.join(tuning_dir, combo_name)}/\n")
    
    print(f"\nMove probability tuning results saved to: {tuning_dir}/")
    print(f"Summary: {summary_log_path}")
    print(f"\nFolder structure:")
    print(f"├── {tuning_dir}/")
    print(f"│   ├── move_probability_tuning_summary_[timestamp].log")
    for combo_name, _ in sorted_results:
        print(f"│   ├── {combo_name}/")
        for run in range(1, num_runs_per_config + 1):
            print(f"│   │   └── run_{run}.log")
    
    return best_overall_schedule
def run_local_search_benchmark(schedule: Schedule, log_file_path: str = None) -> Schedule:
    """
    Run a benchmark of the local search algorithm with various configurations.
    """
    # Create benchmark_tests directory if it doesn't exist
    benchmark_dir = "benchmark_tests"
    os.makedirs(benchmark_dir, exist_ok=True)
    
    iterations_per_temperature = [1000, 2000, 3000, 4000, 5000]
    max_time_seconds = 60 * 2
    start_temps = [200, 300, 400, 500, 600]
    end_temps = [1, 10, 20, 30, 40]
    results = []
    
    # Store the original schedule to copy from for each test
    original_schedule = copy.deepcopy(schedule)
    
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
                    
                    # **KEY FIX: Create a fresh copy of the original schedule for each test**
                    test_schedule = copy.deepcopy(original_schedule)
                    
                    # Run the simulation on the fresh copy
                    start_time = time.time()
                    optimized_schedule = simulated_annealing(
                        test_schedule,  # Use the fresh copy instead of the modified schedule
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
        
        # Rest of the function remains the same...
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

def run_focused_benchmark(schedule: Schedule, num_runs_per_config: int = 5, max_time_seconds: int = 180) -> Schedule:
    """
    Run a focused benchmark on the top performing configurations with multiple runs each.
    """
    import copy
    import statistics
    
    # Create benchmark_tests directory if it doesn't exist
    benchmark_dir = "benchmark_tests"
    os.makedirs(benchmark_dir, exist_ok=True)
    
    # Create separate folder for focused benchmark
    focused_dir = os.path.join(benchmark_dir, "focused_benchmark")
    os.makedirs(focused_dir, exist_ok=True)
    
    # Top 5 configurations from previous benchmark
    top_configs = [
        (2000, 200, 20, "Config1_2000_200_20"),
        (4000, 500, 20, "Config2_4000_500_20"), 
        (5000, 500, 10,  "Config3_5000_500_10"),
        (3000, 300, 20, "Config4_3000_300_20"),
        (5000, 400, 40, "Config5_5000_400_40")
    ]
    
    # Store the original schedule
    original_schedule = copy.deepcopy(schedule)
    
    # Create detailed log file in focused directory
    detailed_log_path = os.path.join(focused_dir, f"focused_benchmark_summary_{int(time.time())}.log")
    
    print("Running focused benchmark on top 5 configurations:")
    print(f"Number of runs per configuration: {num_runs_per_config}")
    print(f"Max time per run: {max_time_seconds} seconds")
    print(f"Results will be saved to: {focused_dir}/")
    print("=" * 80)
    
    all_results = {}
    best_overall_score = float('inf')
    best_overall_schedule = None
    best_overall_config = None
    
    with open(detailed_log_path, 'w') as detailed_log:
        detailed_log.write("FOCUSED BENCHMARK - TOP 5 CONFIGURATIONS\n")
        detailed_log.write(f"Runs per configuration: {num_runs_per_config}\n")
        detailed_log.write(f"Max time per run: {max_time_seconds} seconds\n")
        detailed_log.write(f"Results directory: {focused_dir}\n")
        detailed_log.write("=" * 80 + "\n\n")
        
        for config_idx, (iters, start_temp, end_temp, config_name) in enumerate(top_configs, 1):
            print(f"\n[{config_idx}/5] Testing {config_name}: Iters={iters}, Start={start_temp}, End={end_temp}")
            print("-" * 60)
            
            detailed_log.write(f"CONFIGURATION {config_idx}: {config_name}\n")
            detailed_log.write(f"Parameters: Iters={iters}, Start={start_temp}, End={end_temp}\n")
            detailed_log.write("-" * 60 + "\n")
            
            config_results = []
            config_runtimes = []
            
            # Create subdirectory for this configuration's runs
            config_dir = os.path.join(focused_dir, config_name)
            os.makedirs(config_dir, exist_ok=True)
            
            for run in range(1, num_runs_per_config + 1):
                print(f"  Run {run}/{num_runs_per_config}...", end="", flush=True)
                
                # Create fresh copy for this run
                test_schedule = copy.deepcopy(original_schedule)
                
                # Individual run log in config subdirectory
                run_log_path = os.path.join(config_dir, f"run_{run}.log")
                
                # Run the algorithm
                start_time = time.time()
                optimized_schedule = simulated_annealing(
                    test_schedule,
                    iters,
                    max_time_seconds,
                    start_temp,
                    end_temp,
                    log_file_path=run_log_path
                )
                end_time = time.time()
                
                final_score = calculate_full_score(optimized_schedule)[0]
                runtime = end_time - start_time
                
                config_results.append(final_score)
                config_runtimes.append(runtime)
                
                print(f" Score: {final_score:.0f} ({runtime:.1f}s)")
                
                detailed_log.write(f"Run {run}: Score={final_score:.0f}, Runtime={runtime:.1f}s, Log: {run_log_path}\n")
                
                # Track best overall
                if final_score < best_overall_score:
                    best_overall_score = final_score
                    best_overall_schedule = copy.deepcopy(optimized_schedule)
                    best_overall_config = f"{config_name}_run{run}"
            
            # Calculate statistics for this configuration
            mean_score = statistics.mean(config_results)
            std_score = statistics.stdev(config_results) if len(config_results) > 1 else 0
            min_score = min(config_results)
            max_score = max(config_results)
            mean_runtime = statistics.mean(config_runtimes)
            
            all_results[config_name] = {
                'params': (iters, start_temp, end_temp),
                'scores': config_results,
                'runtimes': config_runtimes,
                'mean_score': mean_score,
                'std_score': std_score,
                'min_score': min_score,
                'max_score': max_score,
                'mean_runtime': mean_runtime
            }
            
            print(f"  → Mean: {mean_score:.0f} ± {std_score:.0f}")
            print(f"  → Range: {min_score:.0f} - {max_score:.0f}")
            print(f"  → Avg Runtime: {mean_runtime:.1f}s")
            
            detailed_log.write(f"Statistics: Mean={mean_score:.0f}, Std={std_score:.0f}, Min={min_score:.0f}, Max={max_score:.0f}\n")
            detailed_log.write(f"Average Runtime: {mean_runtime:.1f}s\n")
            detailed_log.write(f"Individual run logs saved in: {config_dir}/\n\n")
    
    # Final comparison
    print("\n" + "=" * 80)
    print("FOCUSED BENCHMARK RESULTS COMPARISON:")
    print("=" * 80)
    
    # Sort configurations by mean score
    sorted_configs = sorted(all_results.items(), key=lambda x: x[1]['mean_score'])
    
    print(f"{'Rank':<4} {'Configuration':<20} {'Mean Score':<15} {'±Std':<12} {'Best':<15} {'Worst':<15} {'Avg Time':<10}")
    print("-" * 100)
    
    with open(detailed_log_path, 'a') as detailed_log:
        detailed_log.write("=" * 80 + "\n")
        detailed_log.write("FINAL COMPARISON RESULTS:\n")
        detailed_log.write("=" * 80 + "\n")
        detailed_log.write(f"{'Rank':<4} {'Configuration':<20} {'Mean Score':<15} {'±Std':<12} {'Best':<15} {'Worst':<15} {'Avg Time':<10}\n")
        detailed_log.write("-" * 100 + "\n")
        
        for rank, (config_name, results) in enumerate(sorted_configs, 1):
            iters, start_temp, end_temp = results['params']
            result_line = f"{rank:<4} {config_name:<20} {results['mean_score']:<15.0f} ±{results['std_score']:<11.0f} {results['min_score']:<15.0f} {results['max_score']:<15.0f} {results['mean_runtime']:<10.1f}s"
            print(result_line)
            detailed_log.write(result_line + "\n")
        
        # Winner details
        winner_name, winner_results = sorted_configs[0]
        winner_text = f"""
{("=" * 80)}
🏆 WINNER: {winner_name}
{("=" * 80)}
Parameters: Iters={winner_results['params'][0]}, Start={winner_results['params'][1]}, End={winner_results['params'][2]}
Mean Score: {winner_results['mean_score']:.0f} ± {winner_results['std_score']:.0f}
Best Run Score: {winner_results['min_score']:.0f}
Consistency: {winner_results['std_score']/winner_results['mean_score']*100:.2f}% variation
Average Runtime: {winner_results['mean_runtime']:.1f} seconds
{("=" * 80)}
"""
        print(winner_text)
        detailed_log.write(winner_text + "\n")
        
        detailed_log.write(f"\nFOLDER STRUCTURE:\n")
        detailed_log.write(f"Main directory: {focused_dir}/\n")
        detailed_log.write(f"Summary log: {detailed_log_path}\n")
        for config_name, _ in sorted_configs:
            detailed_log.write(f"Config logs: {os.path.join(focused_dir, config_name)}/\n")
    
    print(f"\nAll focused benchmark results saved to: {focused_dir}/")
    print(f"Summary log: {detailed_log_path}")
    print(f"\nFolder structure:")
    print(f"├── {focused_dir}/")
    print(f"│   ├── focused_benchmark_summary_[timestamp].log")
    for config_name, _ in sorted_configs:
        print(f"│   ├── {config_name}/")
        for run in range(1, num_runs_per_config + 1):
            print(f"│   │   └── run_{run}.log")
    
    return best_overall_schedule


def run_local_search_benchmark(schedule: Schedule, log_file_path: str = None) -> Schedule:
    """
    Run a benchmark of the local search algorithm with various configurations.
    """
    # Create benchmark_tests directory if it doesn't exist
    benchmark_dir = "benchmark_tests"
    os.makedirs(benchmark_dir, exist_ok=True)
    
    iterations_per_temperature = [1000, 2000, 3000, 4000, 5000]
    max_time_seconds = 60 * 2
    start_temps = [200, 300, 400, 500, 600]
    end_temps = [1, 10, 20, 30, 40]
    results = []
    
    # Store the original schedule to copy from for each test
    original_schedule = copy.deepcopy(schedule)
    
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
                    
                    # **KEY FIX: Create a fresh copy of the original schedule for each test**
                    test_schedule = copy.deepcopy(original_schedule)
                    
                    # Run the simulation on the fresh copy
                    start_time = time.time()
                    optimized_schedule = simulated_annealing(
                        test_schedule,  # Use the fresh copy instead of the modified schedule
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
        
        # Rest of the function remains the same...
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

def run_focused_benchmark(schedule: Schedule, num_runs_per_config: int = 5, max_time_seconds: int = 180) -> Schedule:
    """
    Run a focused benchmark on the top performing configurations with multiple runs each.
    """
    import copy
    import statistics
    
    # Create benchmark_tests directory if it doesn't exist
    benchmark_dir = "benchmark_tests"
    os.makedirs(benchmark_dir, exist_ok=True)
    
    # Create separate folder for focused benchmark
    focused_dir = os.path.join(benchmark_dir, "focused_benchmark")
    os.makedirs(focused_dir, exist_ok=True)
    
    # Top 5 configurations from previous benchmark
    top_configs = [
        (2000, 200, 20, "Config1_2000_200_20"),
        (4000, 500, 20, "Config2_4000_500_20"), 
        (5000, 500, 10,  "Config3_5000_500_10"),
        (3000, 300, 20, "Config4_3000_300_20"),
        (5000, 400, 40, "Config5_5000_400_40")
    ]
    
    # Store the original schedule
    original_schedule = copy.deepcopy(schedule)
    
    # Create detailed log file in focused directory
    detailed_log_path = os.path.join(focused_dir, f"focused_benchmark_summary_{int(time.time())}.log")
    
    print("Running focused benchmark on top 5 configurations:")
    print(f"Number of runs per configuration: {num_runs_per_config}")
    print(f"Max time per run: {max_time_seconds} seconds")
    print(f"Results will be saved to: {focused_dir}/")
    print("=" * 80)
    
    all_results = {}
    best_overall_score = float('inf')
    best_overall_schedule = None
    best_overall_config = None
    
    with open(detailed_log_path, 'w') as detailed_log:
        detailed_log.write("FOCUSED BENCHMARK - TOP 5 CONFIGURATIONS\n")
        detailed_log.write(f"Runs per configuration: {num_runs_per_config}\n")
        detailed_log.write(f"Max time per run: {max_time_seconds} seconds\n")
        detailed_log.write(f"Results directory: {focused_dir}\n")
        detailed_log.write("=" * 80 + "\n\n")
        
        for config_idx, (iters, start_temp, end_temp, config_name) in enumerate(top_configs, 1):
            print(f"\n[{config_idx}/5] Testing {config_name}: Iters={iters}, Start={start_temp}, End={end_temp}")
            print("-" * 60)
            
            detailed_log.write(f"CONFIGURATION {config_idx}: {config_name}\n")
            detailed_log.write(f"Parameters: Iters={iters}, Start={start_temp}, End={end_temp}\n")
            detailed_log.write("-" * 60 + "\n")
            
            config_results = []
            config_runtimes = []
            
            # Create subdirectory for this configuration's runs
            config_dir = os.path.join(focused_dir, config_name)
            os.makedirs(config_dir, exist_ok=True)
            
            for run in range(1, num_runs_per_config + 1):
                print(f"  Run {run}/{num_runs_per_config}...", end="", flush=True)
                
                # Create fresh copy for this run
                test_schedule = copy.deepcopy(original_schedule)
                
                # Individual run log in config subdirectory
                run_log_path = os.path.join(config_dir, f"run_{run}.log")
                
                # Run the algorithm
                start_time = time.time()
                optimized_schedule = simulated_annealing(
                    test_schedule,
                    iters,
                    max_time_seconds,
                    start_temp,
                    end_temp,
                    log_file_path=run_log_path
                )
                end_time = time.time()
                
                final_score = calculate_full_score(optimized_schedule)[0]
                runtime = end_time - start_time
                
                config_results.append(final_score)
                config_runtimes.append(runtime)
                
                print(f" Score: {final_score:.0f} ({runtime:.1f}s)")
                
                detailed_log.write(f"Run {run}: Score={final_score:.0f}, Runtime={runtime:.1f}s, Log: {run_log_path}\n")
                
                # Track best overall
                if final_score < best_overall_score:
                    best_overall_score = final_score
                    best_overall_schedule = copy.deepcopy(optimized_schedule)
                    best_overall_config = f"{config_name}_run{run}"
            
            # Calculate statistics for this configuration
            mean_score = statistics.mean(config_results)
            std_score = statistics.stdev(config_results) if len(config_results) > 1 else 0
            min_score = min(config_results)
            max_score = max(config_results)
            mean_runtime = statistics.mean(config_runtimes)
            
            all_results[config_name] = {
                'params': (iters, start_temp, end_temp),
                'scores': config_results,
                'runtimes': config_runtimes,
                'mean_score': mean_score,
                'std_score': std_score,
                'min_score': min_score,
                'max_score': max_score,
                'mean_runtime': mean_runtime
            }
            
            print(f"  → Mean: {mean_score:.0f} ± {std_score:.0f}")
            print(f"  → Range: {min_score:.0f} - {max_score:.0f}")
            print(f"  → Avg Runtime: {mean_runtime:.1f}s")
            
            detailed_log.write(f"Statistics: Mean={mean_score:.0f}, Std={std_score:.0f}, Min={min_score:.0f}, Max={max_score:.0f}\n")
            detailed_log.write(f"Average Runtime: {mean_runtime:.1f}s\n")
            detailed_log.write(f"Individual run logs saved in: {config_dir}/\n\n")
    
    # Final comparison
    print("\n" + "=" * 80)
    print("FOCUSED BENCHMARK RESULTS COMPARISON:")
    print("=" * 80)
    
    # Sort configurations by mean score
    sorted_configs = sorted(all_results.items(), key=lambda x: x[1]['mean_score'])
    
    print(f"{'Rank':<4} {'Configuration':<20} {'Mean Score':<15} {'±Std':<12} {'Best':<15} {'Worst':<15} {'Avg Time':<10}")
    print("-" * 100)
    
    with open(detailed_log_path, 'a') as detailed_log:
        detailed_log.write("=" * 80 + "\n")
        detailed_log.write("FINAL COMPARISON RESULTS:\n")
        detailed_log.write("=" * 80 + "\n")
        detailed_log.write(f"{'Rank':<4} {'Configuration':<20} {'Mean Score':<15} {'±Std':<12} {'Best':<15} {'Worst':<15} {'Avg Time':<10}\n")
        detailed_log.write("-" * 100 + "\n")
        
        for rank, (config_name, results) in enumerate(sorted_configs, 1):
            iters, start_temp, end_temp = results['params']
            result_line = f"{rank:<4} {config_name:<20} {results['mean_score']:<15.0f} ±{results['std_score']:<11.0f} {results['min_score']:<15.0f} {results['max_score']:<15.0f} {results['mean_runtime']:<10.1f}s"
            print(result_line)
            detailed_log.write(result_line + "\n")
        
        # Winner details
        winner_name, winner_results = sorted_configs[0]
        winner_text = f"""
{("=" * 80)}
🏆 WINNER: {winner_name}
{("=" * 80)}
Parameters: Iters={winner_results['params'][0]}, Start={winner_results['params'][1]}, End={winner_results['params'][2]}
Mean Score: {winner_results['mean_score']:.0f} ± {winner_results['std_score']:.0f}
Best Run Score: {winner_results['min_score']:.0f}
Consistency: {winner_results['std_score']/winner_results['mean_score']*100:.2f}% variation
Average Runtime: {winner_results['mean_runtime']:.1f} seconds
{("=" * 80)}
"""
        print(winner_text)
        detailed_log.write(winner_text + "\n")
        
        detailed_log.write(f"\nFOLDER STRUCTURE:\n")
        detailed_log.write(f"Main directory: {focused_dir}/\n")
        detailed_log.write(f"Summary log: {detailed_log_path}\n")
        for config_name, _ in sorted_configs:
            detailed_log.write(f"Config logs: {os.path.join(focused_dir, config_name)}/\n")
    
    print(f"\nAll focused benchmark results saved to: {focused_dir}/")
    print(f"Summary log: {detailed_log_path}")
    print(f"\nFolder structure:")
    print(f"├── {focused_dir}/")
    print(f"│   ├── focused_benchmark_summary_[timestamp].log")
    for config_name, _ in sorted_configs:
        print(f"│   ├── {config_name}/")
        for run in range(1, num_runs_per_config + 1):
            print(f"│   │   └── run_{run}.log")
    
    return best_overall_schedule

def run_cooling_rate_tuning(schedule: Schedule, best_config_params: tuple, num_runs_per_config: int = 3, max_time_seconds: int = 120) -> Schedule:
    """
    Tune the K parameter that controls the cooling rate.
    best_config_params should be (iterations, start_temp, end_temp, high_prob, med_prob, low_prob) from your previous best results.
    """
    import copy
    import statistics
    
    # Create benchmark_tests directory if it doesn't exist
    benchmark_dir = "benchmark_tests"
    os.makedirs(benchmark_dir, exist_ok=True)
    
    # Create separate folder for K tuning
    tuning_dir = os.path.join(benchmark_dir, "cooling_rate_tuning")
    os.makedirs(tuning_dir, exist_ok=True)
    
    # Extract best configuration parameters
    best_iters, best_start_temp, best_end_temp, best_high_prob, best_med_prob, best_low_prob = best_config_params
    
    # Define K values to test
    # Format: (K_value, description)
    k_values = [
        (25, "Very_Fast_25"),
        (50, "Fast_Cooling_50"),
        (100, "Current_Baseline_100"),
        (150, "Slow_Cooling_150"),
        (200, "Very_Slow_200"),
        (300, "Extremely_Slow_300"),
    ]
    
    # Store the original schedule
    original_schedule = copy.deepcopy(schedule)
    
    # Create summary log file
    summary_log_path = os.path.join(tuning_dir, f"cooling_rate_tuning_summary_{int(time.time())}.log")
    
    print("Running cooling rate (K parameter) tuning:")
    print(f"Base config: Iters={best_iters}, Start={best_start_temp}, End={best_end_temp}")
    print(f"Move probs: High={best_high_prob}, Med={best_med_prob}, Low={best_low_prob}")
    print(f"Number of K values: {len(k_values)}")
    print(f"Runs per K value: {num_runs_per_config}")
    print(f"Max time per run: {max_time_seconds} seconds")
    print(f"Results will be saved to: {tuning_dir}/")
    print("=" * 80)
    
    all_results = {}
    best_overall_score = float('inf')
    best_overall_schedule = None
    best_overall_config = None
    
    with open(summary_log_path, 'w') as summary_log:
        summary_log.write("COOLING RATE (K PARAMETER) TUNING\n")
        summary_log.write(f"Base configuration: Iters={best_iters}, Start={best_start_temp}, End={best_end_temp}\n")
        summary_log.write(f"Move probabilities: High={best_high_prob}, Med={best_med_prob}, Low={best_low_prob}\n")
        summary_log.write(f"K values tested: {len(k_values)}\n")
        summary_log.write(f"Runs per K value: {num_runs_per_config}\n")
        summary_log.write(f"Max time per run: {max_time_seconds} seconds\n")
        summary_log.write("=" * 80 + "\n\n")
        
        for k_idx, (k_value, k_name) in enumerate(k_values, 1):
            print(f"\n[{k_idx}/{len(k_values)}] Testing {k_name}: K={k_value}")
            
            # Calculate what the cooling rate will be for reference
            cooling_rate = (best_end_temp / best_start_temp) ** (1 / (k_value - 1))
            print(f"  Cooling rate: {cooling_rate:.6f}")
            print("-" * 60)
            
            summary_log.write(f"K VALUE {k_idx}: {k_name}\n")
            summary_log.write(f"K parameter: {k_value}\n")
            summary_log.write(f"Calculated cooling rate: {cooling_rate:.6f}\n")
            summary_log.write("-" * 60 + "\n")
            
            k_results = []
            k_runtimes = []
            
            # Create subdirectory for this K value's runs
            k_dir = os.path.join(tuning_dir, k_name)
            os.makedirs(k_dir, exist_ok=True)
            
            for run in range(1, num_runs_per_config + 1):
                print(f"  Run {run}/{num_runs_per_config}...", end="", flush=True)
                
                # Create fresh copy for this run
                test_schedule = copy.deepcopy(original_schedule)
                
                # Individual run log
                run_log_path = os.path.join(k_dir, f"run_{run}.log")
                
                # Run simulated annealing with modified K value
                start_time = time.time()
                optimized_schedule = simulated_annealing(
                    test_schedule,
                    best_iters,
                    max_time_seconds,
                    best_start_temp,
                    best_end_temp,
                    high_temp_compound_prob=best_high_prob,
                    medium_temp_compound_prob=best_med_prob,
                    low_temp_compound_prob=best_low_prob,
                    K=k_value,  # This is the parameter we're tuning
                    log_file_path=run_log_path
                )
                end_time = time.time()
                
                final_score = calculate_full_score(optimized_schedule)[0]
                runtime = end_time - start_time
                
                k_results.append(final_score)
                k_runtimes.append(runtime)
                
                print(f" Score: {final_score:.0f} ({runtime:.1f}s)")
                
                summary_log.write(f"Run {run}: Score={final_score:.0f}, Runtime={runtime:.1f}s\n")
                
                # Track best overall
                if final_score < best_overall_score:
                    best_overall_score = final_score
                    best_overall_schedule = copy.deepcopy(optimized_schedule)
                    best_overall_config = f"{k_name}_run{run}"
            
            # Calculate statistics
            mean_score = statistics.mean(k_results)
            std_score = statistics.stdev(k_results) if len(k_results) > 1 else 0
            min_score = min(k_results)
            max_score = max(k_results)
            mean_runtime = statistics.mean(k_runtimes)
            
            all_results[k_name] = {
                'k_value': k_value,
                'cooling_rate': cooling_rate,
                'scores': k_results,
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
        print("\n" + "=" * 80)
        print("COOLING RATE (K PARAMETER) TUNING RESULTS:")
        print("=" * 80)
        
        # Sort by mean score
        sorted_results = sorted(all_results.items(), key=lambda x: x[1]['mean_score'])
        
        print(f"{'Rank':<4} {'Configuration':<20} {'K':<6} {'Cooling Rate':<12} {'Mean Score':<12} {'±Std':<10} {'Best':<12}")
        print("-" * 85)
        
        summary_log.write("=" * 80 + "\n")
        summary_log.write("FINAL RESULTS RANKING:\n")
        summary_log.write("=" * 80 + "\n")
        summary_log.write(f"{'Rank':<4} {'Configuration':<20} {'K':<6} {'Cooling Rate':<12} {'Mean Score':<12} {'±Std':<10} {'Best':<12}\n")
        summary_log.write("-" * 85 + "\n")
        
        for rank, (k_name, results) in enumerate(sorted_results, 1):
            result_line = f"{rank:<4} {k_name:<20} {results['k_value']:<6} {results['cooling_rate']:<12.6f} {results['mean_score']:<12.0f} ±{results['std_score']:<9.0f} {results['min_score']:<12.0f}"
            print(result_line)
            summary_log.write(result_line + "\n")
        
        # Winner analysis
        winner_name, winner_results = sorted_results[0]
        
        winner_text = f"""
{("=" * 80)}
🏆 BEST COOLING RATE CONFIGURATION:
{("=" * 80)}
Configuration: {winner_name}
K Parameter: {winner_results['k_value']}
Cooling Rate: {winner_results['cooling_rate']:.6f}
Temperature Steps: {winner_results['k_value']} (controls how gradually temperature decreases)

Performance:
Mean Score: {winner_results['mean_score']:.0f} ± {winner_results['std_score']:.0f}
Best Run: {winner_results['min_score']:.0f}
Consistency: {winner_results['std_score']/winner_results['mean_score']*100:.2f}% variation
Average Runtime: {winner_results['mean_runtime']:.1f} seconds

Interpretation:
"""
        if winner_results['k_value'] < 100:
            winner_text += "Faster cooling (fewer temperature steps) works better - algorithm converges quicker\n"
        elif winner_results['k_value'] > 100:
            winner_text += "Slower cooling (more temperature steps) works better - more gradual exploration\n"
        else:
            winner_text += "Current baseline K=100 is optimal\n"
            
        # Compare to baseline if it exists
        if "Current_Baseline_100" in all_results:
            baseline = all_results["Current_Baseline_100"]
            improvement = baseline['mean_score'] - winner_results['mean_score']
            winner_text += f"Improvement over K=100 baseline: {improvement:.0f} points ({improvement/baseline['mean_score']*100:.2f}%)\n"
        
        winner_text += f"{('=' * 80)}\n"
        
        print(winner_text)
        summary_log.write(winner_text + "\n")
    
    print(f"\nCooling rate tuning results saved to: {tuning_dir}/")
    print(f"Summary: {summary_log_path}")
    
    return best_overall_schedule

