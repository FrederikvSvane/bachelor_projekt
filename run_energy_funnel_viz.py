#!/usr/bin/env python3
"""
Run energy funnel visualization with customizable parameters
"""

import sys
import os
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.util.data_generator import generate_test_data_parsed
from src.construction.heuristic.linear_assignment import generate_schedule
from src.base_model.schedule import Schedule, generate_schedule_using_double_flow
from src.local_search.simulated_annealing import simulated_annealing
from src.local_search.rules_engine import calculate_full_score
from src.util.energy_funnel_visualizer import create_sample_visualization
from src.base_model.compatibility_checks import initialize_compatibility_matricies
from src.util.parser import parse_input
from pathlib import Path
import time


def main():
    parser = argparse.ArgumentParser(description='Generate 3D energy funnel visualization for scheduling optimization')
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--test', type=int, metavar='N_CASES', 
                            help='Generate test data with N cases')
    input_group.add_argument('--input', type=str, metavar='FILE',
                            help='Use input JSON file')
    
    # Construction method
    parser.add_argument('--method', choices=['linear', 'graph'], default='linear',
                       help='Initial construction method (default: linear)')
    
    # Optimization parameters
    parser.add_argument('--time', type=int, default=180,
                       help='Runtime in seconds (default: 180)')
    parser.add_argument('--iterations', type=int, default=5000,
                       help='Iterations per temperature (default: 5000)')
    parser.add_argument('--start-temp', type=float, default=300,
                       help='Starting temperature (default: 300)')
    parser.add_argument('--end-temp', type=float, default=10,
                       help='Ending temperature (default: 10)')
    
    # Visualization parameters
    parser.add_argument('--log-interval', type=int, default=50,
                       help='Log every N iterations (default: 50)')
    parser.add_argument('--demo', action='store_true',
                       help='Also create demo visualization with synthetic data')
    
    args = parser.parse_args()
    
    print("3D Energy Funnel Visualization")
    print("=" * 50)
    
    # Create demo if requested
    if args.demo:
        print("\nCreating demo visualization with synthetic data...")
        create_sample_visualization()
        print("✓ Demo saved to: src/util/data_visualizer/energy_funnel_demo.html")
    
    # Load or generate data
    if args.test:
        print(f"\nGenerating test data with {args.test} cases...")
        parsed_data = generate_test_data_parsed(
            n_cases=args.test,
            work_days=5,
            granularity=5,
            min_per_work_day=390
        )
    else:
        print(f"\nLoading data from {args.input}...")
        parsed_data = parse_input(Path(args.input))
    
    # Initialize compatibility matrices
    initialize_compatibility_matricies(parsed_data)
    
    # Create initial schedule
    print(f"\nCreating initial schedule using {args.method} method...")
    if args.method == 'linear':
        schedule = generate_schedule(parsed_data)
    else:
        schedule = generate_schedule_using_double_flow(parsed_data)
    
    # Prepare schedule for optimization
    schedule.initialize_appointment_chains()
    schedule.trim_schedule_length_if_possible()
    
    # Check initial quality
    initial_score, hard, medium, soft = calculate_full_score(schedule)
    print(f"\nInitial schedule:")
    print(f"  Score: {initial_score:,} (Hard: {hard}, Medium: {medium}, Soft: {soft})")
    print(f"  Planned: {len(list(schedule.iter_appointments()))}")
    print(f"  Unplanned: {len(schedule.unplanned_meetings)}")
    
    # Run optimization with visualization
    print(f"\nRunning simulated annealing:")
    print(f"  Runtime: {args.time} seconds")
    print(f"  Iterations/temp: {args.iterations}")
    print(f"  Temperature: {args.start_temp} → {args.end_temp}")
    print(f"  Logging interval: every {args.log_interval} iterations")
    print("\nOptimizing...\n")
    
    # Configure logger
    from src.util.sa_logger import SimulatedAnnealingLogger
    original_log_interval = SimulatedAnnealingLogger.__init__.__defaults__[0]
    SimulatedAnnealingLogger.__init__.__defaults__ = (args.log_interval,)
    
    start_time = time.time()
    optimized_schedule = simulated_annealing(
        schedule,
        iterations_per_temperature=args.iterations,
        max_time_seconds=args.time,
        start_temp=args.start_temp,
        end_temp=args.end_temp,
        enable_3d_visualization=True
    )
    elapsed_time = time.time() - start_time
    
    # Final results
    final_score, hard, medium, soft = calculate_full_score(optimized_schedule)
    print(f"\n{'=' * 50}")
    print(f"Optimization complete in {elapsed_time:.1f} seconds!")
    print(f"\nFinal schedule:")
    print(f"  Score: {final_score:,} (Hard: {hard}, Medium: {medium}, Soft: {soft})")
    print(f"  Improvement: {initial_score - final_score:,} points ({(1 - final_score/initial_score)*100:.1f}%)")
    
    print(f"\n✓ 3D visualization saved to: src/util/data_visualizer/energy_funnel_*.html")
    print("\nOpen the HTML file in your browser to explore the search landscape!")


if __name__ == "__main__":
    main()