#!/usr/bin/env python3
"""
Simple benchmarking script for the Court Case Scheduler.
Tests cases from 100 to 1500 in steps of 10, outputs only cases,time to CSV.
"""

import csv
import time
import sys
from pathlib import Path

# Import the main scheduler functions directly
sys.path.append('.')
from src.util.data_generator import generate_test_data_parsed
from src.base_model.compatibility_checks import initialize_compatibility_matricies
from src.construction.heuristic.linear_assignment import generate_schedule
from src.local_search.simulated_annealing import run_local_search
from src.local_search.rules_engine import calculate_full_score


def calculate_days_for_cases(n_cases: int) -> int:
    """Calculate appropriate number of days based on linear scaling."""
    # Linear relationship: 500 cases = 30 days, 250 cases = 15 days
    # So days = cases * 0.06
    return max(5, int(n_cases * 0.06))


def run_single_test(n_cases: int) -> float:
    """
    Run scheduler for given number of cases and return time taken.
    
    Args:
        n_cases: Number of cases to test
        
    Returns:
        Time taken in seconds
    """
    start_time = time.time()
    
    try:
        # Generate test data
        n_work_days = calculate_days_for_cases(n_cases)
        parsed_data = generate_test_data_parsed(n_cases, n_work_days, granularity=5, min_per_work_day=390)
        
        # Initialize compatibility matrices
        initialize_compatibility_matricies(parsed_data)
        
        # Generate initial schedule using heuristic method
        initial_schedule = generate_schedule(parsed_data)
        initial_schedule.initialize_appointment_chains()
        initial_schedule.trim_schedule_length_if_possible()
        
        # Run local search until hard constraints eliminated or timeout
        final_schedule = run_local_search(initial_schedule)  # 5 min timeout
        
        # Check if we eliminated hard constraints
        result = calculate_full_score(final_schedule)
        hard_violations = result[1]
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"Cases: {n_cases:4d}, Time: {elapsed_time:6.1f}s, Hard violations: {hard_violations}")
        
        return elapsed_time
        
    except Exception as e:
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Cases: {n_cases:4d}, Time: {elapsed_time:6.1f}s, ERROR: {str(e)}")
        return elapsed_time


def main():
    """Run benchmark from 100 to 1500 cases in steps of 10 and save to CSV."""
    output_file = 'benchmark_results.csv'
    
    # Test cases from 100 to 1500 in steps of 10
    case_counts = list(range(100, 1501, 10))
    
    print(f"Running benchmark for {len(case_counts)} configurations")
    print(f"Range: 100 to 1500 cases (step 10)")
    print(f"Output: {output_file}")
    print("-" * 50)
    
    results = []
    
    for i, n_cases in enumerate(case_counts, 1):
        print(f"[{i:3d}/{len(case_counts)}] Testing {n_cases} cases...")
        
        elapsed_time = run_single_test(n_cases)
        results.append((n_cases, elapsed_time))
    
    # Save to CSV
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['cases', 'time'])
        writer.writerows(results)
    
    print(f"\nResults saved to {output_file}")
    print(f"Tested {len(results)} configurations")


if __name__ == "__main__":
    main()