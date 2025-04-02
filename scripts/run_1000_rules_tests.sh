#!/bin/bash

failure_count=0

for i in {1..1000}
do
  echo "Run #$i"
  
  # Run the command and capture its output - using command substitution that preserves output
  output=$(python -m unittest tests.test_rules_engine 2>&1)
  
  # Check if the last line is "OK"
  if ! echo "$output" | grep -q "OK$"; then
    failure_count=$((failure_count + 1))
    echo "Test failed on run #$i"
    echo "$output"
  fi
  
  # Optional: print a short status update every 100 runs
  if (( i % 100 == 0 )); then
    echo "Completed $i runs. Failures so far: $failure_count"
  fi
done

echo "All 1000 runs completed. Total failures: $failure_count"