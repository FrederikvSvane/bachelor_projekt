#!/bin/bash
# Configuration
OUTPUT_CSV="ilp_search_runtime.csv"
MAX_CASES=80
STEP=5
MAX_DAYS=30
ILP_TIMEOUT=1800
ILP_PARAM2=100

# Create CSV header
echo "n_cases,n_work_days,runtime_seconds,cumulative_runtime,status" > "$OUTPUT_CSV"
cumulative_runtime=0

# Function to kill all child processes
cleanup() {
    echo "Cleaning up processes..."
    pkill -P $$
    exit 1
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Function to test feasibility with proper cleanup
test_feasibility() {
    local n_cases=$1
    local n_work_days=$2
    local temp_output="feasibility_test_${n_cases}_${n_work_days}.txt"
    
    echo "    Quick feasibility test: $n_cases cases, $n_work_days days"
    
    # Start the process in background with unbuffered output
    stdbuf -o0 python -u -m src.main --method=ilp --ilp-params 120 100 --test "$n_cases" "$n_work_days" > "$temp_output" 2>&1 &
    local python_pid=$!
    
    # Wait for either completion or timeout (120 seconds)
    local count=0
    local max_wait=120
    while kill -0 "$python_pid" 2>/dev/null && [ $count -lt $max_wait ]; do
        sleep 1
        ((count++))
        
        # Print progress every 10 seconds
        if [ $((count % 10)) -eq 0 ]; then
            echo "      Waiting... ${count}s elapsed"
        fi
        
        # Check if we have enough output to determine feasibility
        if [ -f "$temp_output" ]; then
            if grep -q "Infeasible" "$temp_output"; then
                echo "      Found infeasible at ${count}s - killing process"
                kill -9 "$python_pid" 2>/dev/null
                wait "$python_pid" 2>/dev/null
                rm -f "$temp_output"
                return 1  # Infeasible
            elif grep -q "Continuous objective value" "$temp_output"; then
                echo "      Found feasible at ${count}s - killing process"
                kill -9 "$python_pid" 2>/dev/null
                wait "$python_pid" 2>/dev/null
                rm -f "$temp_output"
                return 0  # Feasible
            fi
        fi
    done
    
    # If we get here, either timeout or process died
    echo "      Timeout at ${count}s or error - killing process"
    if [ -f "$temp_output" ]; then
        echo "      Last few lines of output:"
        tail -5 "$temp_output"
    fi
    kill -9 "$python_pid" 2>/dev/null
    wait "$python_pid" 2>/dev/null
    rm -f "$temp_output"
    return 2  # Timeout/error
}

# Function to cleanup any lingering processes
cleanup_processes() {
    pkill -f "python -m src.main" 2>/dev/null || true
    sleep 2
}

# Loop through case counts
for ((n_cases=1; n_cases<=MAX_CASES; n_cases+=STEP)); do
    echo "Finding minimum feasible days for n_cases: $n_cases"
    
    # Try increasing days until feasible solution is found
    feasible_found=false
    min_feasible_days=0
    
    for ((n_work_days=1; n_work_days<=MAX_DAYS; n_work_days++)); do
        test_feasibility "$n_cases" "$n_work_days"
        result=$?
        
        if [ $result -eq 0 ]; then
            # Feasible found
            echo "    Feasible with $n_work_days days!"
            min_feasible_days=$n_work_days
            feasible_found=true
            break
        elif [ $result -eq 1 ]; then
            # Infeasible, continue
            echo "    Infeasible with $n_work_days days"
            cleanup_processes
            continue
        else
            # Error/timeout, continue
            echo "    Error/timeout with $n_work_days days"
            cleanup_processes
            continue
        fi
    done
    
    # If feasible solution found, now do the actual timed benchmark
    if [ "$feasible_found" = true ]; then
        echo "Running full benchmark: n_cases: $n_cases, n_work_days: $min_feasible_days"
        
        # Wait a bit for full cleanup
        sleep 3
        
        # Create temporary output file for the actual benchmark
        temp_output="benchmark_${n_cases}.txt"
        
        # Time the full execution with unbuffered output
        start_time=$(date +%s.%N)
        
        if timeout "$ILP_TIMEOUT" stdbuf -o0 python -u -m src.main --method=ilp --ilp-params "$ILP_TIMEOUT" "$ILP_PARAM2" --test "$n_cases" "$min_feasible_days" > "$temp_output" 2>&1; then
            end_time=$(date +%s.%N)
            runtime=$(echo "$end_time - $start_time" | bc -l)
            cumulative_runtime=$(echo "$cumulative_runtime + $runtime" | bc -l)
            
            # Write to CSV
            printf "%d,%d,%.1f,%.1f,solved\n" "$n_cases" "$min_feasible_days" "$runtime" "$cumulative_runtime" >> "$OUTPUT_CSV"
            
            # Print to terminal
            printf "ILP - n_cases: %d, min_days: %d, runtime: %.1f, cumulative_runtime: %.1f\n" "$n_cases" "$min_feasible_days" "$runtime" "$cumulative_runtime"
        else
            end_time=$(date +%s.%N)
            runtime=$(echo "$end_time - $start_time" | bc -l)
            cumulative_runtime=$(echo "$cumulative_runtime + $runtime" | bc -l)
            
            echo "Timeout or error in benchmark run for $n_cases cases"
            printf "%d,%d,%.1f,%.1f,timeout\n" "$n_cases" "$min_feasible_days" "$runtime" "$cumulative_runtime" >> "$OUTPUT_CSV"
        fi
        
        rm -f "$temp_output"
        
        # Cleanup any remaining processes
        cleanup_processes
    else
        # No feasible solution found within MAX_DAYS
        echo "  No feasible solution found for $n_cases cases within $MAX_DAYS days"
        printf "%d,%d,-1,%.1f,no_feasible\n" "$n_cases" "$MAX_DAYS" "$cumulative_runtime" >> "$OUTPUT_CSV"
    fi
    
    echo "Completed $n_cases cases. Moving to next..."
    echo "----------------------------------------"
done

echo "ILP benchmark completed. Results saved to $OUTPUT_CSV"