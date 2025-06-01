import time
import csv
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.base_model.schedule import generate_schedule_using_double_flow
from src.util.data_generator import generate_test_data_parsed 

OUTPUT_CSV = "graph_sol_runtime_log.csv"

def benchmark_schedule_generation():
    n_work_days = 10
    granularity = 5
    min_per_work_day = 390
    max_cases = 1500  # Conservative limit for 2-hour total runtime
    step = 10

    with open(OUTPUT_CSV, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["n_cases", "runtime_seconds", "days_used", "unmatched_to_judges", "unmatched_to_rooms", "total_meetings"])

        cumulative_runtime = 0

        for n_cases in range(10, max_cases + 1, step):
            parsed_data = generate_test_data_parsed(n_cases, n_work_days, granularity, min_per_work_day)
            
            # Count total meetings
            total_meetings = sum(len(case.meetings) for case in parsed_data["cases"])

            start = time.perf_counter()
            
            # Capture warnings about unmatched assignments
            import warnings
            unmatched_to_judges = 0
            unmatched_to_rooms = 0
            
            with warnings.catch_warnings(record=True) as warning_list:
                warnings.simplefilter("always")
                
                try:
                    schedule = generate_schedule_using_double_flow(parsed_data)
                    end = time.perf_counter()
                    
                    # Check for unmatched warnings
                    for w in warning_list:
                        if "Not all cases could be assigned judges" in str(w.message):
                            # Extract numbers from warning message
                            msg = str(w.message)
                            parts = msg.split()
                            found_idx = parts.index("Found")
                            needed_idx = parts.index("needed")
                            found = int(parts[found_idx + 1])
                            needed = int(parts[needed_idx + 1].rstrip('.'))
                            unmatched_to_judges = needed - found
                    
                    # Calculate days used by examining the schedule
                    days_used = schedule.work_days
                    
                except RuntimeError as e:
                    # Handle room assignment failures
                    if "Not all judge-case pairs could be assigned rooms" in str(e):
                        end = time.perf_counter()
                        msg = str(e)
                        parts = msg.split()
                        found_idx = parts.index("Found")
                        needed_idx = parts.index("needed")
                        found = int(parts[found_idx + 1])
                        needed = int(parts[needed_idx + 1].rstrip('.'))
                        unmatched_to_rooms = needed - found
                        days_used = -1  # Indicate failure
                        schedule = None
                    else:
                        raise

            runtime = end - start
            cumulative_runtime += runtime
            
            print(f"n_cases: {n_cases}, runtime: {runtime:.4f}s, cumulative: {cumulative_runtime:.1f}s, days: {days_used}, "
                  f"unmatched to judges: {unmatched_to_judges}, unmatched to rooms: {unmatched_to_rooms}")
            
            writer.writerow([n_cases, runtime, days_used, unmatched_to_judges, unmatched_to_rooms, total_meetings])
            file.flush()  # Ensure data is written immediately

if __name__ == "__main__":
    benchmark_schedule_generation()
