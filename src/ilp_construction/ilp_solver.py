import pulp
from typing import Dict
from src.base_model import Case, Judge, Room, Appointment
from src.base_model.schedule import Schedule
import time

def generate_schedule_using_ilp(parsed_data: Dict) -> Schedule:
    """
    Generate a schedule using Integer Linear Programming approach.
    """

    work_days = parsed_data["work_days"]
    minutes_in_a_work_day = parsed_data["min_per_work_day"]
    granularity = parsed_data["granularity"]
    cases = parsed_data["cases"]
    judges = parsed_data["judges"]
    rooms = parsed_data["rooms"]
    
    timeslots_per_day = minutes_in_a_work_day // granularity
    total_timeslots = work_days * timeslots_per_day
    
    # Define flattened time slot range
    T_f = range(1, total_timeslots + 1) # we add 1 cause its exclusive
    print(T_f)
    
    # Create the ILP problem
    problem = pulp.LpProblem("CourtCaseScheduling", pulp.LpMinimize)
    
    # Start timer for performance tracking
    start_time = time.time()
    
    print("Creating decision variables...")
    
    # Decision variables
    # a[c][j][r][t] = 1 if case c is assigned to judge j in room r at time t
    a = {}
    for c in cases:
        a[c.case_id] = {}
        for j in judges:
            a[c.case_id][j.judge_id] = {}
            for r in rooms:
                a[c.case_id][j.judge_id][r.room_id] = {}
                for t in T_f:
                    a[c.case_id][j.judge_id][r.room_id][t] = pulp.LpVariable(
                        f"a_{c.case_id}_{j.judge_id}_{r.room_id}_{t}", 
                        cat=pulp.LpBinary
                    )
    
    # Variables to track segment starts and ends
    s = {}  # s[c][t] = 1 if case c starts a segment at time t
    e = {}  # e[c][t] = 1 if case c ends a segment at time t
    
    for c in cases:
        s[c.case_id] = {}
        e[c.case_id] = {}
        for t in T_f:
            s[c.case_id][t] = pulp.LpVariable(f"s_{c.case_id}_{t}", cat=pulp.LpBinary)
            e[c.case_id][t] = pulp.LpVariable(f"e_{c.case_id}_{t}", cat=pulp.LpBinary)
    
    print(f"Variables created in {time.time() - start_time:.2f} seconds")
    start_time = time.time()
    
    print("Adding constraints...")
    
    # Constraint 1: Each case must be scheduled for its required duration
    for c in cases:
        problem += (
            pulp.lpSum(
                a[c.case_id][j.judge_id][r.room_id][t]
                for j in judges
                for r in rooms
                for t in T_f
            ) == c.case_duration // granularity, #the amount of timeslots needed for the case
            f"Coverage_Case_{c.case_id}"
        )
        print(f"Case {c.case_id} must be scheduled for {c.case_duration // granularity} timeslots")
    
    # Constraint 2: No room double-booking
    for r in rooms:
        for t in T_f:
            problem += (
                pulp.lpSum(
                    a[c.case_id][j.judge_id][r.room_id][t]
                    for c in cases
                    for j in judges
                ) <= 1,
                f"No_Room_Double_Booking_{r.room_id}_{t}"
            )
    
    # Constraint 3: No judge double-booking
    for j in judges:
        for t in T_f:
            problem += (
                pulp.lpSum(
                    a[c.case_id][j.judge_id][r.room_id][t]
                    for c in cases
                    for r in rooms
                ) <= 1,
                f"No_Judge_Double_Booking_{j.judge_id}_{t}"
            )
    
    # Constraint 4: Judge-Case compatibility
    for c in cases:
        for j in judges:
            # Create binary parameter for compatibility
            compatible = 1 if is_compatible(c, j) else 0
            if compatible == 1:
                print(f"Case {c.case_id} and Judge {j.judge_id} are compatible")
            
            if compatible == 0:
                for r in rooms:
                    for t in T_f:
                        problem += (
                            a[c.case_id][j.judge_id][r.room_id][t] == 0,
                            f"Judge_Case_Compatibility_{c.case_id}_{j.judge_id}_{r.room_id}_{t}"  # Include room_id in name to avoid conflicts
                        )

    # Constraint 5: Case-Room compatibility
    for c in cases:
        for r in rooms:
            # Create binary parameter for compatibility
            compatible = 1 if is_room_compatible(c, r) else 0
            if compatible == 1:
                print(f"Case {c.case_id} and Room {r.room_id} are compatible")
            
            if compatible == 0:
                for j in judges:
                    for t in T_f:
                        problem += (
                            a[c.case_id][j.judge_id][r.room_id][t] == 0,
                            f"Case_Room_Compatibility_{c.case_id}_{j.judge_id}_{r.room_id}_{t}"  # same
                        )

    # Constraint 6: Judge-Room compatibility
    for j in judges:
        for r in rooms:
            # Create binary parameter for compatibility
            compatible = 1 if is_judge_room_compatible(j, r) else 0
            if compatible == 1:
                print(f"Judge {j.judge_id} and Room {r.room_id} are compatible")
            
            if compatible == 0:
                for c in cases:
                    for t in T_f:
                        problem += (
                            a[c.case_id][j.judge_id][r.room_id][t] == 0,
                            f"Judge_Room_Compatibility_{c.case_id}_{j.judge_id}_{r.room_id}_{t}"  # same
                        )
    
    
    '''
    # Segment tracking constraints
    
    # For first time slot, segment starts if case is scheduled
    for c in cases:
        problem += (
            s[c.case_id][1] >= pulp.lpSum(
                a[c.case_id][j.judge_id][r.room_id][1]
                for j in judges
                for r in rooms
            ),
            f"Segment_Start_First_{c.case_id}"
        )
    
    # For other time slots, segment starts if case is scheduled at t but not at t-1
    for c in cases:
        for t in range(2, total_timeslots + 1):
            problem += (
                s[c.case_id][t] >= pulp.lpSum(
                    a[c.case_id][j.judge_id][r.room_id][t]
                    for j in judges
                    for r in rooms
                ) - pulp.lpSum(
                    a[c.case_id][j.judge_id][r.room_id][t-1]
                    for j in judges
                    for r in rooms
                ),
                f"Segment_Start_{c.case_id}_{t}"
            )
    
    # For last time slot, segment ends if case is scheduled
    for c in cases:
        problem += (
            e[c.case_id][total_timeslots] >= pulp.lpSum(
                a[c.case_id][j.judge_id][r.room_id][total_timeslots]
                for j in judges
                for r in rooms
            ),
            f"Segment_End_Last_{c.case_id}"
        )
    
    # For other time slots, segment ends if case is scheduled at t but not at t+1
    for c in cases:
        for t in range(1, total_timeslots):
            problem += (
                e[c.case_id][t] >= pulp.lpSum(
                    a[c.case_id][j.judge_id][r.room_id][t]
                    for j in judges
                    for r in rooms
                ) - pulp.lpSum(
                    a[c.case_id][j.judge_id][r.room_id][t+1]
                    for j in judges
                    for r in rooms
                ),
                f"Segment_End_{c.case_id}_{t}"
            )
    
    print(f"Constraints added in {time.time() - start_time:.2f} seconds")
    start_time = time.time()
    
    # Define objective function - minimize number of segments
    w_break = 100  # Penalty weight for breaking cases
    
    # Sum of all segment starts (minus 1 per case, as each case needs at least one segment)
    segment_penalty = pulp.lpSum(
        pulp.lpSum(s[c.case_id][t] for t in T_f) - 1
        for c in cases
    ) * w_break
    
    # Set the objective function - minimize the segment penalty
    problem += segment_penalty, "Minimize_Segment_Breaks"
    '''
    
    # Solve the problem with a time limit
    print("Solving the ILP model...")
    start_time = time.time()

    # Set a reasonable time limit
    problem.solve(pulp.GLPK_CMD(msg=True, timeLimit=60))

    solution_time = time.time() - start_time
    print(f"ILP solved in {solution_time:.2f} seconds with status: {pulp.LpStatus[problem.status]}")

    schedule = Schedule(work_days, minutes_in_a_work_day, granularity)

    # Extract solution - properly handle any status
    if problem.status == pulp.LpStatusOptimal:
        print("Optimal solution found!")
    elif problem.status == pulp.LpStatusUndefined:
        print("Time limit reached - extracting best solution found (if any)")
    else:
        print(f"No solution found. Status: {pulp.LpStatus[problem.status]}")

    # Try to extract any solution if variables have values
    feasible_solution_found = False
    for c in cases:
        for j in judges:
            for r in rooms:
                for t in T_f:
                    var = a[c.case_id][j.judge_id][r.room_id][t]
                    val = pulp.value(var)
                    if val is not None and val > 0.5:  # If assignment is 1
                        feasible_solution_found = True
                        # Calculate day and timeslot within day
                        day = (t - 1) // timeslots_per_day
                        timeslot_in_day = (t - 1) % timeslots_per_day
                        
                        appointment = Appointment(
                            case=c,
                            judge=j,
                            room=r,
                            day=day,
                            timeslot_start=timeslot_in_day,
                            timeslots_duration=granularity
                        )
                        schedule.appointments.append(appointment)

    if not feasible_solution_found:
        print("No feasible solution could be found.")

    return schedule

def is_compatible(case: Case, judge: Judge) -> bool:
    """Check if a case and judge are compatible"""
    # Check if the judge has all required attributes
    for req in case.judge_requirements:
        if req not in judge.characteristics:
            return False
    
    # Check if the case has all required attributes
    for req in judge.case_requirements:
        if req not in case.characteristics:
            return False
    
    return True

def is_room_compatible(case: Case, room: Room) -> bool:
    """Check if a case and room are compatible"""
    # Check if the room has all required attributes
    for req in case.room_requirements:
        if req not in room.characteristics:
            return False
    
    # Check if the case has all required attributes
    for req in room.case_requirements:
        if req not in case.characteristics:
            return False
    
    return True

def is_judge_room_compatible(judge: Judge, room: Room) -> bool:
    """Check if a judge and room are compatible"""
    # Check if the room has all required attributes
    for req in judge.room_requirements:
        if req not in room.characteristics:
            return False
    
    # Check if the judge has all required attributes
    for req in room.judge_requirements:
        if req not in judge.characteristics:
            return False
    
    return True