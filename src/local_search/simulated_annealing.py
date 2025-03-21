import math
import random
from copy import deepcopy
from typing import Dict, List

from src.base_model.schedule import Schedule
from src.local_search.move import apply_move, undo_move, Move
from src.local_search.move_generator import generate_random_move, calculate_compatible_judges, calculate_compatible_rooms
from src.local_search.rules_engine import calculate_score, print_score_summary

def calculate_alpha(K: int, start_temperature: float, end_temperature: float) -> float:
    """
    Calculate the cooling rate alpha for simulated annealing.
    
    Args:
        K: Number of temperature steps
        start_temperature: Starting temperature
        end_temperature: Ending temperature
        
    Returns:
        Alpha cooling rate
    """
    return (end_temperature / start_temperature) ** (1 / (K - 1))

def simulated_annealing(schedule: Schedule, n: int, K: int, 
                        start_temp: float, end_temp: float) -> Schedule:
    """
    Perform simulated annealing optimization on the given schedule.
    
    Args:
        schedule: Initial schedule
        n: Problem size factor for iteration calculation
        K: Number of temperature steps
        start_temp: Starting temperature
        end_temp: Ending temperature
        
    Returns:
        Optimized schedule
    """
    iterations_per_temperature = n * (n - 1) // 2
    alpha = calculate_alpha(K, start_temp, end_temp)
    
    cases = schedule.get_all_cases()
    judges = schedule.get_all_judges()
    rooms = schedule.get_all_rooms() 
    
    compatible_judges = calculate_compatible_judges(cases, judges)
    compatible_rooms = calculate_compatible_rooms(cases, rooms) 
    # print the len of compatible_judges and compatible_rooms for each case
    # for case_id in compatible_judges:
    #     print(f"Case {case_id}: Judges {len(compatible_judges[case_id])}, Rooms {len(compatible_rooms[case_id])}")
    
    current_score = calculate_score(schedule, move=Move(case_id=1, appointments=[]), initial_calculation=True)
    best_score = current_score
    best_schedule = deepcopy(schedule)  # Only deep copy once at the beginning
    
    temperature = start_temp
    total_moves = 0
    accepted_moves = 0
    
    for k in range(K):
        iteration_accepted = 0
        
        for i in range(iterations_per_temperature):
            # Generate and apply a move
            move = generate_random_move(schedule, compatible_judges, compatible_rooms)
            
            # Skip empty moves
            if (move.new_judge is None and move.new_room is None and 
                move.new_day is None and move.new_start_timeslot is None):
                print("wtf")
                continue
                
            apply_move(move)
            total_moves += 1
            
            # Calculate new score
            new_score = calculate_score(schedule, move)
            
            # Accept or reject move
            delta = new_score - current_score
            if delta < 0 or random.random() < math.exp(-delta / temperature):
                # Accept move
                current_score = new_score
                iteration_accepted += 1
                accepted_moves += 1
                
                # Update best solution if needed
                if current_score < best_score:
                    best_score = current_score
                    best_schedule = deepcopy(schedule)  # Only deep copy for best solution
                    
            else:
                # Reject move - undo it
                undo_move(move)
        
        temperature *= alpha
        print(f"Iteration {k+1}/{K} - Temp: {temperature:.2f}, "
              f"Accepted: {iteration_accepted}/{iterations_per_temperature}, "
              f"Current: {current_score}, Best: {best_score}")
        
        # Early termination if no progress
        if iteration_accepted == 0:
            print("Early termination: No moves accepted in this iteration")
            break
    
    print(f"Search completed: {total_moves} moves attempted, {accepted_moves} accepted")
    print_score_summary(best_schedule)
    return best_schedule

def run_local_search(schedule: Schedule) -> Schedule:
    """
    Run simulated annealing with parameter testing to find optimal settings.
    
    Args:
        schedule: Initial schedule
        
    Returns:
        Optimized schedule
    """
    initial_schedule = deepcopy(schedule)
    initial_score = calculate_score(schedule, move=Move(case_id=1, appointments=[]), initial_calculation=True)
    print(f"Initial score: {initial_score}")
    
    # Parameter ranges to test
    start_temperatures = [300]
    end_temperatures = [1]
    iteration_counts = [40]
    
    # Track results
    results = []
    best_score = float('inf')
    best_schedule = None
    best_params = None
    
    total_combinations = len(start_temperatures) * len(end_temperatures) * len(iteration_counts)
    
    print(f"Testing {total_combinations} parameter combinations...\n")
    print(f"{'Start Temp':^10} | {'End Temp':^8} | {'K':^4} | {'Score':^6}")
    print("-" * 35)
    
    best_schedule = simulated_annealing(
        initial_schedule,
        iteration_counts[0],
        100,  # Number of temperature steps
        start_temperatures[0],
        end_temperatures[0]
    )
    # for start_temp in start_temperatures:
    #     for end_temp in end_temperatures:
    #         for n in iteration_counts:
    #             # Create a fresh copy of the initial schedule
    #             test_schedule = deepcopy(initial_schedule)
                
    #             # Run simulated annealing
    #             optimized_schedule = simulated_annealing(
    #                 test_schedule,
    #                 n,
    #                 100,  # Number of temperature steps
    #                 start_temp,
    #                 end_temp
    #             )
                
    #             # Calculate score of the optimized schedule
    #             score = calculate_score(optimized_schedule)
                
    #             # Print result for this combination
    #             print(f"{start_temp:^10} | {end_temp:^8} | {n:^4} | {score:^6}")
                
    #             # Save result
    #             result = {
    #                 "start_temp": start_temp,
    #                 "end_temp": end_temp,
    #                 "n": n,
    #                 "score": score,
    #                 "schedule": optimized_schedule
    #             }
    #             results.append(result)
                
    #             # Update best result if better
    #             if score < best_score:
    #                 best_score = score
    #                 best_schedule = optimized_schedule
    #                 best_params = (start_temp, end_temp, n)
    
    # Print summary
    print("\n==== PARAMETER TESTING SUMMARY ====")
    print(f"Initial score: {initial_score}")
    print(f"Best score: {best_score}")
    print(f"Best parameters: start_temp={best_params[0]}, end_temp={best_params[1]}, n={best_params[2]}")
    
    return best_schedule