#!/bin/bash

n_tests=1000

all="tests.test_rules_engine"

room_overbookings="tests.test_rules_engine.TestRulesEngine.test_nr1_overbooked_room_in_timeslot"
judge_overbookings="tests.test_rules_engine.TestRulesEngine.test_nr2_overbooked_judge_in_timeslot"
time_grain="tests.test_rules_engine.TestRulesEngine.test_nr18_unused_timegrain"
room_stability="tests.test_rules_engine.TestRulesEngine.test_nr29_room_stability_per_day"
all_delta_rules="tests.test_rules_engine.TestRulesEngine.test_all_delta_functions"

# ____

to_test=$time_grain

# ____


failure_count=0
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