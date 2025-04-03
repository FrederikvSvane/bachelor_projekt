#!/bin/bash

failure_count=0
n_tests=1000
to_test="tests.test_rules_engine.TestRulesEngine.test_nr18_unused_timegrain"
echo "Running test: $to_test for $n_tests times"
for i in $(seq 1 $n_tests); 
do
  echo "Run #$i"
  
  # Run the command and capture its output - using command substitution that preserves output
  output=$(python -m unittest $to_test 2>&1)
  
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