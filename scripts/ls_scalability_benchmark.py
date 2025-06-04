import time
import csv
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# Import the necessary modules from your codebase
from src.util.data_generator import generate_test_data_parsed
from src.base_model.compatibility_checks import initialize_compatibility_matricies
from src.construction.heuristic.linear_assignment import generate_schedule
from src.local_search.simulated_annealing import simulated_annealing
from src.local_search.rules_engine import calculate_full_score

OUTPUT_CSV = "local_search_runtime_log.csv"

def benchmark_local_search():
    granularity = 5
    min_per_work_day = 390
    max_cases = 2000  # Conservative limit
    step = 50
    days_per_case = 0.052 # Scale factor: ~0.06 days per case
    
    with open(OUTPUT_CSV, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            "n_cases", 
            "n_work_days",
            "runtime_seconds", 
            "cumulative_runtime",
            "days_used", 
            "initial_hard_violations"
        ])
        
        cumulative_runtime = 0
        
        for n_cases in range(10, max_cases + 1, step):
            # Scale work days with number of cases
            n_work_days = max(1, int(n_cases * days_per_case + 3.21))          
            # Generate test data
            parsed_data = generate_test_data_parsed(n_cases, n_work_days, granularity, min_per_work_day)
            
            try:
                # Initialize compatibility matrices
                initialize_compatibility_matricies(parsed_data)
                
                # Generate initial schedule using heuristic (same as in main.py)
                initial_schedule = generate_schedule(parsed_data)
                initial_schedule.trim_schedule_length_if_possible()
                initial_schedule.initialize_appointment_chains()
                
                # Calculate initial score
                initial_result = calculate_full_score(initial_schedule)
                initial_hard = initial_result[1]
                
                # Run local search with unlimited time
                start = time.perf_counter()
                
                optimized_schedule = simulated_annealing(
                    initial_schedule,
                    iterations_per_temperature=4000,
                    max_time_seconds=float('inf'),  # Unlimited time
                    start_temp=500,
                    end_temp=20,
                    K=75
                )
                
                end = time.perf_counter()
                
                runtime = end - start
                cumulative_runtime += runtime
                
                # Get days used from optimized schedule
                days_used = optimized_schedule.work_days
                
                # Log results to CSV
                writer.writerow([
                    n_cases,
                    n_work_days,
                    runtime,
                    cumulative_runtime,
                    days_used,
                    initial_hard
                ])
                
                # Print only the requested columns to terminal
                print(f"n_cases: {n_cases}, runtime: {runtime:.1f}, cumulative_runtime: {cumulative_runtime:.1f}, days: {days_used}, initial_hard: {initial_hard}")
                
            except Exception as e:
                print(f"Error with {n_cases} cases: {str(e)}")
                # Log failed attempt
                writer.writerow([
                    n_cases,
                    n_work_days,
                    -1,  # Error indicator
                    cumulative_runtime,
                    -1,
                    -1
                ])
            
            file.flush()  # Ensure data is written immediately

if __name__ == "__main__":
    benchmark_local_search()