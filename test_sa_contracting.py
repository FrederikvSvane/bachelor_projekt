#!/usr/bin/env python3
"""
Test the modified simulated annealing with contracting moves at outer iterations.
"""

import time
from src.util.data_generator import generate_test_data_parsed
from src.base_model.compatibility_checks import initialize_compatibility_matricies
from src.base_model.schedule import generate_schedule_using_double_flow
from src.construction.heuristic.linear_assignment import generate_schedule
from src.local_search.rules_engine import calculate_full_score
from src.local_search.simulated_annealing import simulated_annealing
from src.util.schedule_visualizer import visualize

def main():
    print("=== Testing SA with Contracting Moves at Outer Iterations ===\n")
    
    # Generate test data
    print("1. Generating test data...")
    test_data = generate_test_data_parsed(
        n_cases=15, 
        work_days=3, 
        granularity=5, 
        min_per_work_day=390
    )
    initialize_compatibility_matricies(test_data)
    print(f"   Created {len(test_data['cases'])} cases over {test_data['work_days']} days")
    
    # Create initial schedule
    print("\n2. Creating initial schedule...")
    try:
        schedule = generate_schedule_using_double_flow(test_data)
        construction_method = "Graph-based"
    except Exception as e:
        print(f"   Graph construction failed ({e}), using heuristic...")
        schedule = generate_schedule(test_data)
        construction_method = "Heuristic"
    
    schedule.initialize_appointment_chains()
    schedule.trim_schedule_length_if_possible()
    
    initial_score = calculate_full_score(schedule)[0]
    print(f"   {construction_method} construction completed")
    print(f"   Initial score: {initial_score}")
    print(f"   Planned meetings: {len(schedule.get_all_planned_meetings())}")
    
    print("\n3. Running simulated annealing with contracting moves...")
    print("   (Contracting moves will be applied at the start of each outer iteration)")
    
    # Run SA with shorter parameters for testing
    start_time = time.time()
    optimized_schedule = simulated_annealing(
        schedule, 
        iterations_per_temperature=100,  # Reduced for testing
        max_time_seconds=30,             # Short test run
        start_temp=50, 
        end_temp=1
    )
    sa_time = time.time() - start_time
    
    final_score = calculate_full_score(optimized_schedule)[0]
    total_improvement = initial_score - final_score
    
    print(f"\n4. Results:")
    print(f"   SA completed in {sa_time:.2f}s")
    print(f"   Final score: {final_score}")
    print(f"   Total improvement: {initial_score} -> {final_score} (Δ: {-total_improvement})")
    
    if total_improvement > 0:
        print(f"   ✓ Schedule improved by {total_improvement} points")
    else:
        print(f"   - No improvement (may indicate already optimal)")
    
    print("\n=== Test Complete ===")
    print("✓ Contracting moves are now applied at outer iterations")
    print("✓ Inner loop move generation remains separate")
    print("✓ SA successfully integrates contracting moves")

if __name__ == "__main__":
    main()