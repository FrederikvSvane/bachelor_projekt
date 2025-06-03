#!/bin/bash
# Configuration
OUTPUT_CSV="ilp_search_runtime.csv"
MAX_CASES=70
STEP=5
DAYS_PER_CASE=0.061
ILP_TIMEOUT=1800
ILP_PARAM2=100

# Create CSV header
echo "n_cases,n_work_days,runtime_seconds,cumulative_runtime,days_used" > "$OUTPUT_CSV"
cumulative_runtime=0

# Loop through case counts
for ((n_cases=1; n_cases<=MAX_CASES; n_cases+=STEP)); do
    # Calculate work days using the same formula
    n_work_days=$(python3 -c "import math; print(math.floor($n_cases * $DAYS_PER_CASE))")
    if [ "$n_work_days" -lt 1 ]; then
        n_work_days=1
    fi
    
    echo "Running ILP solver - n_cases: $n_cases, n_work_days: $n_work_days"
    
    # Create temporary output file for this run
    temp_output="temp_ilp_output_${n_cases}.txt"
    
    # Time the execution and capture output
    start_time=$(date +%s.%N)
    
    # Run the ILP solver command and capture output
    if python -m src.main --method=ilp --ilp-params "$ILP_TIMEOUT" "$ILP_PARAM2" --test "$n_cases" "$n_work_days" > "$temp_output" 2>&1; then
        end_time=$(date +%s.%N)
        runtime=$(echo "$end_time - $start_time" | bc -l)
        cumulative_runtime=$(echo "$cumulative_runtime + $runtime" | bc -l)
        
        # Write to CSV
        printf "%d,%d,%.1f,%.1f\n" "$n_cases" "$n_work_days" "$runtime" "$cumulative_runtime" >> "$OUTPUT_CSV"
        
        # Print to terminal
        printf "ILP - n_cases: %d, runtime: %.1f, cumulative_runtime: %.1f\n" "$n_cases" "$runtime" "$cumulative_runtime"
    else
        end_time=$(date +%s.%N)
        runtime=$(echo "$end_time - $start_time" | bc -l)
        cumulative_runtime=$(echo "$cumulative_runtime + $runtime" | bc -l)
        
        echo "Error with ILP solver for $n_cases cases:"
        echo "============ ERROR OUTPUT ============"
        cat "$temp_output"
        echo "======================================"
        
        # Write error to CSV
        printf "%d,%d,-1,%.1f,-1,-1\n" "$n_cases" "$n_work_days" "$cumulative_runtime" >> "$OUTPUT_CSV"
    fi
    
    # Clean up temp file
    rm -f "$temp_output"
done

echo "ILP benchmark completed. Results saved to $OUTPUT_CSV"