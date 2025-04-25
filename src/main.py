import argparse
import json
from pathlib import Path
import sys

from src.util.parser import parse_input
from src.base_model.schedule import Schedule, generate_schedule_using_double_flow
from src.util.schedule_visualizer import visualize
from src.local_search.rules_engine import calculate_full_score
from src.local_search.simulated_annealing import run_local_search
from src.base_model.compatibility_checks import initialize_compatibility_matricies
from src.local_search.move import Move, do_move, undo_move
from src.local_search.move_generator import generate_delete_move, generate_compound_move
from src.heuristic_construction.linear_assignment import generate_schedule

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Court Case Scheduler')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--input', type=str, help='Path to input JSON file')
    
    group.add_argument('--test', nargs='+', type=int, 
                       help='Generate test data with [n_cases] [n_judges] [n_rooms] [n_work_days]')
    
    parser.add_argument('--method', type=str, choices=['graph', 'ilp', 'heuristic'], default='graph',
                        help='Method to use for scheduling (default: graph)')
    
    parser.add_argument('--output', type=str, default='output.json',
                      help='Path to output JSON file (default: output.json)')
    
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
            if len(args.test) < 4:
                print("Error: Test mode requires 3 parameters: n_cases n_judges n_rooms n_work_days")
                return 1
            
            from src.util.data_generator import generate_test_data_parsed
            n_cases, n_judges, n_rooms, n_work_days = args.test[:4]
            parsed_data: dict = generate_test_data_parsed(n_cases, n_judges, n_rooms, n_work_days, granularity=5, min_per_work_day=390)
        

        initialize_compatibility_matricies(parsed_data)
        
        # Choose initial schedule construction method
        if args.method == 'ilp':
            print("Using ILP-based scheduling method")
            from src.ilp_construction.ilp_solver import generate_schedule_using_ilp
            initial_schedule: Schedule = generate_schedule_using_ilp(parsed_data)
        elif args.method == 'graph':
            print("Using graph-based scheduling method")
            initial_schedule: Schedule = generate_schedule_using_double_flow(parsed_data)
        elif args.method == 'heuristic':
            print("Using heuristic-based scheduling method")
            initial_schedule: Schedule = generate_schedule(parsed_data)


        
        # ___ main operations ___'
        #final_schedule = initial_schedule
        #final_schedule.move_all_dayboundary_violations()
        #visualize(final_schedule)
        #initial_score = calculate_full_score(final_schedule)
        #print("Initial score: ", initial_score)
        
        # _______________________
        initial_schedule.initialize_appointment_chains()
        initial_schedule.move_all_dayboundary_violations()
        initial_schedule.trim_schedule_length_if_possible()
        initial_score = calculate_full_score(initial_schedule)
        visualize(initial_schedule)
        
        final_schedule = run_local_search(initial_schedule)
        
        final_score = calculate_full_score(final_schedule)
        visualize(final_schedule)
        print(f"Initial score: {initial_score}")
        print(f"Final score: {final_score}")

        # final_score = calculate_full_score(final_schedule)
        # visualize(final_schedule)
        # print(f"Initial score: {initial_score}")
        # print(f"Final score: {final_score}")        
        # _______________________
        
        # visualize(initial_schedule)
        # for app in initial_schedule.iter_appointments():
        #     print(app)
        # initial_schedule.print_unplanned_meetings()        

        # all_meetings = initial_schedule.get_all_meetings()
        
        # first_meeting = all_meetings[0]
        # first_meeting_id = first_meeting.meeting_id 
        # move: Move = generate_delete_move(initial_schedule, first_meeting_id)
        # print(f"Generated move: {move}")
        # print(f"Move uses the judge {move.old_judge} and room {move.old_room}")
        # do_move(move, initial_schedule)
        
        # visualize(initial_schedule)
        # for app in initial_schedule.iter_appointments():
        #     print(app)
        # initial_schedule.print_unplanned_meetings()        
        
        # undo_move(move, initial_schedule)
        # visualize(initial_schedule)
        # for app in initial_schedule.iter_appointments():
        #     print(app)
        # initial_schedule.print_unplanned_meetings()        
        
        # final_schedule = initial_schedule
        # _______________________



        # Write schedule to output file
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