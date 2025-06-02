#!/bin/bash
# Configuration
OUTPUT_CSV="local_search_runtime_log_2000_3000.csv"
MAX_CASES=3000
STEP=20
DAYS_PER_CASE=0.061
# Create CSV header
echo "n_cases,n_work_days,runtime_seconds,cumulative_runtime,days_used,initial_hard_violations" > "$OUTPUT_CSV"
cumulative_runtime=0
# Loop through case counts
for ((n_cases=2000; n_cases<=MAX_CASES; n_cases+=STEP)); do
    # Calculate work days using the same formula
    n_work_days=$(echo "$n_cases * $DAYS_PER_CASE + 3.21" | bc -l | cut -d. -f1)
    if [ "$n_work_days" -lt 1 ]; then
        n_work_days=1
    fi
    
    echo "Running n_cases: $n_cases, n_work_days: $n_work_days"
    
    # Create temporary output file for this run
    temp_output="temp_output_${n_cases}.txt"
    
    # Time the execution and capture output
    start_time=$(date +%s.%N)
    
    # Run the python command and capture output
    if python -m src.main --method=heuristic --test "$n_cases" "$n_work_days" > "$temp_output" 2>&1; then
        end_time=$(date +%s.%N)
        runtime=$(echo "$end_time - $start_time" | bc -l)
        cumulative_runtime=$(echo "$cumulative_runtime + $runtime" | bc -l)
        
        # Extract metrics from output (you may need to adjust these patterns based on actual output)
        days_used=-1
        initial_hard=-1
        
        # Try to extract days from output (adjust pattern as needed)
        if grep -q "days:" "$temp_output"; then
            days_used=$(grep "days:" "$temp_output" | grep -o "[0-9]\+" | head -1)
        fi
        
        # Try to extract initial hard violations (adjust pattern as needed)
        if grep -q "Hard violations:" "$temp_output"; then
            initial_hard=$(grep "Hard violations:" "$temp_output" | grep -o "[0-9]\+" | head -1)
        fi
        
        # If we can't extract values, set defaults
        if [ -z "$days_used" ] || [ "$days_used" == "" ]; then
            days_used=-1
        fi
        if [ -z "$initial_hard" ] || [ "$initial_hard" == "" ]; then
            initial_hard=-1
        fi
        
        # Write to CSV
        printf "%d,%d,%.1f,%.1f,%d,%d\n" "$n_cases" "$n_work_days" "$runtime" "$cumulative_runtime" "$days_used" "$initial_hard" >> "$OUTPUT_CSV"
        
        # Print to terminal
        printf "n_cases: %d, runtime: %.1f, cumulative_runtime: %.1f, days: %d, initial_hard: %d\n" "$n_cases" "$runtime" "$cumulative_runtime" "$days_used" "$initial_hard"
        
    else
        end_time=$(date +%s.%N)
        runtime=$(echo "$end_time - $start_time" | bc -l)
        cumulative_runtime=$(echo "$cumulative_runtime + $runtime" | bc -l)
        
        echo "Error with $n_cases cases:"
        echo "============ ERROR OUTPUT ============"
        cat "$temp_output"
        echo "======================================"
        
        # Write error to CSV
        printf "%d,%d,-1,%.1f,-1,-1\n" "$n_cases" "$n_work_days" "$cumulative_runtime" >> "$OUTPUT_CSV"
    fi
    
    # Clean up temp file
    rm -f "$temp_output"
done
echo "Benchmark completed. Results saved to $OUTPUT_CSV"