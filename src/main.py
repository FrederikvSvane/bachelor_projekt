import argparse
import json
from pathlib import Path
import sys
import os


from src.parser import parse_input
from src.schedule import generate_schedule_using_double_flow
import src.calendar_visualizer as calendar_visualizer
from src.calendar_visualizer import calendar_visualizer
from src.rules_engine import calculate_score

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Court Case Scheduler')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--input', type=str, help='Path to input JSON file')
    group.add_argument('--test', nargs='+', type=int, 
                       help='Generate test data with [n_cases] [n_judges] [n_rooms]')
    
    parser.add_argument('--output', type=str,
                      help='Path to output JSON file (default: output.json)',
                      default='output.json')
    
    return parser.parse_args()

def main():
    """Main entry point for the scheduler."""
    args = parse_arguments()
    
    try:
        # Handle input data
        if args.input:
            input_path = Path(args.input)
            if not input_path.exists():
                print(f"Error: Input file {args.input} not found")
                return 1
            parsed_data = parse_input(input_path)
        else:  # Test mode
            if len(args.test) < 3:
                print("Error: Test mode requires 3 parameters: n_cases n_judges n_rooms")
                return 1
            
            from src.data_generator import generate_test_data_parsed
            n_cases, n_judges, n_rooms = args.test[:3]
            parsed_data = generate_test_data_parsed(n_cases, n_judges, n_rooms)
        
        schedule = generate_schedule_using_double_flow(parsed_data)
        visualizer = calendar_visualizer(parsed_data["judges"], parsed_data["rooms"], parsed_data["cases"], schedule)
        visualizer.generate_calendar()
        
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        score = calculate_score(schedule)
        print(f"Final score: {score}")
        
        with open(output_path, 'w') as f:
            json.dump(schedule.to_json(), f, indent=2)
        
        print(f"Schedule written to {args.output}")
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())