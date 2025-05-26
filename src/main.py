import argparse
import json
from pathlib import Path
import sys

from src.util.parser import parse_input
from src.base_model.schedule import Schedule, generate_schedule_using_double_flow
from src.util.schedule_visualizer import visualize
from src.local_search.rules_engine import calculate_full_score
from src.local_search.simulated_annealing import run_local_search, run_move_probability_and_threshold_tuning
from src.base_model.compatibility_checks import initialize_compatibility_matricies, case_room_matrix
from src.local_search.move import Move, do_move, undo_move
from src.local_search.move_generator import generate_specific_delete_move, generate_compound_move
from src.construction.heuristic.linear_assignment import generate_schedule
import random

random.seed(13062025)  # Set seed for reproducibility

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Court Case Scheduler')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--input', type=str, help='Path to input JSON file')
    
    group.add_argument('--test', nargs='+', type=int, 
                       help='Generate test data with [n_cases] [n_work_days]')
    
    parser.add_argument('--method', type=str, choices=['graph', 'ilp', 'heuristic'], default='graph',
                        help='Method to use for scheduling (default: graph)')
    
    parser.add_argument('--output', type=str, default='output.json',
                      help='Path to output JSON file (default: output.json)')
    
    parser.add_argument('--log', type=str, help='Path to log file for simulated annealing output')

    parser.add_argument('--time', type=int, help='Time for local search in seconds')
    
    return parser.parse_args()

def main():
    """Main entry point for the scheduler."""
    args = parse_arguments()
    
    try:
        # Handle input data (use input file or generate test data)
        if args.input:
            input_path = Path(args.input)
            if not input_path.exists():
                print(f"Error: Input file {args.input} not found")
                return 1
            parsed_data = parse_input(input_path)
        elif args.test: 
            if len(args.test) < 2:
                print("Error: Test mode requires 2 parameters: n_cases n_work_days")
                return 1
            
            from src.util.data_generator import generate_test_data_parsed
            n_cases, n_work_days = args.test[:2]
            parsed_data: dict = generate_test_data_parsed(n_cases, n_work_days, granularity=5, min_per_work_day=390)
        

        initialize_compatibility_matricies(parsed_data)
        
        # --- Start: Concise Check ---
        all_case_ids = {case.case_id for case in parsed_data["cases"]}
        if not all_case_ids.issubset(case_room_matrix.keys()):
             missing_ids = all_case_ids - case_room_matrix.keys()
             raise ValueError(f"Error: Case IDs missing from case_room_matrix: {missing_ids}")
        else:
            print("All case IDs are present in case_room_matrix.")
        # --- End: Concise Check ---

        
        # Choose initial schedule construction method
        if args.method == 'ilp':
            print("Using ILP-based scheduling method")
            from src.construction.ilp import generate_schedule_using_ilp
            initial_schedule: Schedule = generate_schedule_using_ilp(parsed_data)
        elif args.method == 'graph':
            print("Using graph-based scheduling method")
            initial_schedule: Schedule = generate_schedule_using_double_flow(parsed_data)
        elif args.method == 'heuristic':
            print("Using heuristic-based scheduling method")
            initial_schedule: Schedule = generate_schedule(parsed_data)

    
        
        #_______________________
        initial_schedule.initialize_appointment_chains()
        #initial_schedule.move_all_dayboundary_violations()
        initial_schedule.trim_schedule_length_if_possible()
        result = calculate_full_score(initial_schedule)
        initial_score = result[0]
        hard_violations = result[1]
        medm_violations = result[2]
        soft_violations = result[3]
        #visualize(initial_schedule)
        #visualize(initial_schedule, view_by="room")
        print(f"Hard violations: {hard_violations}, Medium violations: {medm_violations}, Soft violations: {soft_violations}")
        print(f"Initial score: {initial_score}")
        
        # In your main function, use:
        #final_schedule = run_local_search(initial_schedule, args.log)  
        #final_schedule = run_local_search_benchmark(initial_schedule, args.log)

        #best_params = (4000, 200, 30, 0.3, 0.5, 0.7)  # Your best config: (iterations, start_temp, end_temp)
        #final_schedule = run_cooling_rate_tuning(initial_schedule, best_params, num_runs_per_config=2, max_time_seconds=600)
#        final_schedule = run_focused_benchmark(initial_schedule, 2, max_time_seconds=120)

        best_params = (4000, 500, 20)  # Your best configuration: (iterations, start_temp, end_temp)
        final_schedule = run_move_probability_and_threshold_tuning(
            initial_schedule, 
            best_params, 
            num_runs_per_config=1,  # 3 runs per configuration (adjust as needed)
            max_time_seconds=300   # 2 minutes per run (adjust as needed)
        )

        final_score = calculate_full_score(final_schedule)
        #visualize(final_schedule)
        # visualize(final_schedule, view_by="room")
        print(f"Initial score: {initial_score}")
        print(f"Final score: {final_score}")
        #___________________________________________

        final_score = calculate_full_score(final_schedule)
        #visualize(final_schedule)
        print(f"Initial score: {initial_score}")
        print(f"Final score: {final_score}")        
        #_______________________
        
        #Write schedule to output file
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(final_schedule.to_json(), f, indent=2)
        print(f"Schedule written to {args.output}")

        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())