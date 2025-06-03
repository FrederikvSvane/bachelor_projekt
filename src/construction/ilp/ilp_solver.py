import pulp
from typing import Dict
from src.base_model.appointment import Appointment
from src.base_model.schedule import Schedule
from src.base_model.compatibility_checks import (
    case_judge_compatible,
    case_room_compatible,
    judge_room_compatible
)
import time

def generate_schedule_using_ilp(parsed_data: Dict, time_limit: int = 60, gap_rel: float = 0.005) -> Schedule:
    """
    Generate a schedule using Integer Linear Programming approach.
    Meetings are scheduled as contiguous blocks of time slots.
    Uses day/timeslot structure without flattening.
    
    Args:
        parsed_data: Dictionary containing the scheduling data
        time_limit: Maximum time in seconds for the solver (default: 60)
        gap_rel: Relative optimality gap for early termination (default: 0.005 = 0.5%)
    """

    work_days = parsed_data["work_days"]
    minutes_in_a_work_day = parsed_data["min_per_work_day"]
    granularity = parsed_data["granularity"]
    cases = parsed_data["cases"]
    judges = parsed_data["judges"]
    rooms = parsed_data["rooms"]
    meetings = parsed_data.get("meetings", [])
    
    # If meetings not provided, extract from cases
    if not meetings:
        meetings = []
        for case in cases:
            meetings.extend(case.meetings)
    
    timeslots_per_day = minutes_in_a_work_day // granularity
    
    # Create the ILP problem (minimize medium and soft constraint violations)
    problem = pulp.LpProblem("CourtCaseScheduling", pulp.LpMinimize)
    
    # Start timer for performance tracking
    start_time = time.time()
    
    print("Creating decision variables...")
    
    # Pre-filter compatible combinations to reduce variable count
    compatible_assignments = []
    for m in meetings:
        for j in judges:
            if case_judge_compatible(m.case, j):
                for r in rooms:
                    if case_room_compatible(m.case, r) and judge_room_compatible(j, r):
                        compatible_assignments.append((m, j, r))
    
    print(f"Found {len(compatible_assignments)} compatible (meeting, judge, room) combinations")
    
    # Decision variables using sparse representation
    # x[(m_id, j_id, r_id, d, t)] = 1 if meeting m starts at day d, timeslot t with judge j in room r
    x = {}
    meeting_duration_slots = {}  # Cache duration calculations
    
    for m, j, r in compatible_assignments:
        duration_slots = m.meeting_duration // granularity
        meeting_duration_slots[m.meeting_id] = duration_slots
        
        for d in range(1, work_days + 1):
            # Only create variables for timeslots where the meeting can fit within the day
            max_start_slot = timeslots_per_day - duration_slots + 1
            for t in range(1, max_start_slot + 1):
                key = (m.meeting_id, j.judge_id, r.room_id, d, t)
                x[key] = pulp.LpVariable(f"x_{key}", cat=pulp.LpBinary)
    
    # Variables for optimization objectives
    
    # Track the maximum day used (minimize schedule length)
    max_day_used = pulp.LpVariable("max_day_used", lowBound=1, upBound=work_days, cat=pulp.LpInteger)
    
    # Binary variables: day_used[d] = 1 if any meeting is scheduled on day d
    day_used = {}
    for d in range(1, work_days + 1):
        day_used[d] = pulp.LpVariable(f"day_used_{d}", cat=pulp.LpBinary)
    
    # Room stability variables - efficient formulation
    # y[(j_id, r_id, d)] = 1 if judge j uses room r on day d (at least once)
    # Only create y variables for combinations that can actually occur
    y = {}
    possible_jrd = set()
    for m, j, r in compatible_assignments:
        for d in range(1, work_days + 1):
            possible_jrd.add((j.judge_id, r.room_id, d))
    
    for j_id, r_id, d in possible_jrd:
        key = (j_id, r_id, d)
        y[key] = pulp.LpVariable(f"y_{key}", cat=pulp.LpBinary)
    
    
    
    
    print(f"Variables created in {time.time() - start_time:.2f} seconds")
    start_time = time.time()
    
    print("Adding constraints...")
    
    # Hard constraints:
    
    # Constraint 1: Each meeting must be scheduled exactly once
    for m in meetings:
        valid_starts = [
            x[key] for key in x.keys() 
            if key[0] == m.meeting_id  # meeting_id is first element of tuple
        ]
        
        if valid_starts:
            problem += (
                pulp.lpSum(valid_starts) == 1,
                f"Schedule_Meeting_Once_{m.meeting_id}"
            )
    
    # Constraint 2: No room double-booking (optimized)
    # Pre-group variables by room and day for faster lookup
    room_day_vars = {}
    for key in x.keys():
        m_id, j_id, r_id, day, start_t = key
        if (r_id, day) not in room_day_vars:
            room_day_vars[(r_id, day)] = []
        room_day_vars[(r_id, day)].append((key, meeting_duration_slots[m_id]))
    
    for r in rooms:
        for d in range(1, work_days + 1):
            room_day_key = (r.room_id, d)
            if room_day_key not in room_day_vars:
                continue
                
            for t in range(1, timeslots_per_day + 1):
                occupancy_sum = []
                
                for key, duration_slots in room_day_vars[room_day_key]:
                    _, _, _, _, start_t = key
                    if start_t <= t <= start_t + duration_slots - 1:
                        occupancy_sum.append(x[key])
                
                if occupancy_sum:
                    problem += (
                        pulp.lpSum(occupancy_sum) <= 1,
                        f"No_Room_Double_Booking_{r.room_id}_{d}_{t}"
                    )
    
    # Constraint 3: No judge double-booking (optimized)
    # Pre-group variables by judge and day for faster lookup
    judge_day_vars = {}
    for key in x.keys():
        m_id, j_id, r_id, day, start_t = key
        if (j_id, day) not in judge_day_vars:
            judge_day_vars[(j_id, day)] = []
        judge_day_vars[(j_id, day)].append((key, meeting_duration_slots[m_id]))
    
    for j in judges:
        for d in range(1, work_days + 1):
            judge_day_key = (j.judge_id, d)
            if judge_day_key not in judge_day_vars:
                continue
                
            for t in range(1, timeslots_per_day + 1):
                occupancy_sum = []
                
                for key, duration_slots in judge_day_vars[judge_day_key]:
                    _, _, _, _, start_t = key
                    if start_t <= t <= start_t + duration_slots - 1:
                        occupancy_sum.append(x[key])
                
                if occupancy_sum:
                    problem += (
                        pulp.lpSum(occupancy_sum) <= 1,
                        f"No_Judge_Double_Booking_{j.judge_id}_{d}_{t}"
                    )
    
    # Constraints 4-6: Compatibility constraints are now handled by pre-filtering
    # We only create variables for compatible combinations, so no additional constraints needed
    
    
    # Constraint for schedule length optimization:
    
    # Link day_used to meeting assignments
    # If any meeting is scheduled on a day, that day is used
    for d in range(1, work_days + 1):
        meetings_on_day = [x[key] for key in x.keys() if key[3] == d]
        if meetings_on_day:
            problem += (
                day_used[d] >= pulp.lpSum(meetings_on_day) / len(meetings_on_day),
                f"Day_Used_{d}"
            )
    
    # Link max_day_used to day_used
    # max_day_used must be at least as large as any day that is used
    for d in range(1, work_days + 1):
        problem += (
            max_day_used >= d * day_used[d],
            f"Max_Day_Used_{d}"
        )
    
    # Room stability constraints - link y variables to x variables
    # Pre-compute x variables grouped by judge, room, and day
    x_by_jrd = {}
    for key in x.keys():
        m_id, j_id, r_id, day, start_t = key
        jrd_key = (j_id, r_id, day)
        if jrd_key not in x_by_jrd:
            x_by_jrd[jrd_key] = []
        x_by_jrd[jrd_key].append(x[key])
    
    # Link y variables: y[j,r,d] = 1 if judge j has any meeting in room r on day d
    for y_key in y.keys():
        jrd_key = y_key  # They're the same format
        
        if jrd_key in x_by_jrd:
            # y = 1 if any x variable for this judge/room/day is 1
            x_vars = x_by_jrd[jrd_key]
            problem += (
                y[y_key] <= pulp.lpSum(x_vars),
                f"Y_Upper_Bound_{y_key}"
            )
            # Force y = 1 if any meeting happens
            problem += (
                y[y_key] >= pulp.lpSum(x_vars) / len(x_vars),
                f"Y_Lower_Bound_{y_key}"
            )
    
    
    
    
    print(f"Constraints added in {time.time() - start_time:.2f} seconds")
    
    # Objective function: minimize schedule length (primary), room diversity (secondary), and start time (tertiary)
    # Add a small penalty for meetings that start later in the day to encourage early/packed scheduling
    start_time_penalty = pulp.lpSum([
        (start_t - 1) * x[key]  # Penalty increases with later start times
        for key in x.keys()
        for m_id, j_id, r_id, d, start_t in [key]
    ])
    
    # Room stability penalty: sum of y variables (number of different rooms used per judge per day)
    # The fewer rooms a judge uses per day, the better
    room_diversity_penalty = pulp.lpSum([
        y[key] for key in y.keys()
    ])
    
    # Case-judge consistency penalty - very efficient approach
    # Add a small penalty based on judge ID to encourage consistent judge assignment per case
    case_judge_penalty = 0
    
    # Create a mapping of meeting to case
    meeting_to_case = {m.meeting_id: m.case.case_id for m in meetings}
    
    # Create case-specific judge preferences
    # This encourages meetings from the same case to pick the same judge
    # by giving each judge a different penalty offset per case
    case_judge_offset = {}
    for c_idx, c in enumerate(cases):
        for j_idx, j in enumerate(judges):
            # Small unique offset per case-judge pair
            case_judge_offset[(c.case_id, j.judge_id)] = j_idx * 0.001  # Reduced from 0.1 to 0.001
    
    # Apply the penalty in the objective
    for key in x.keys():
        m_id, j_id, r_id, day, start_t = key
        c_id = meeting_to_case[m_id]
        if (c_id, j_id) in case_judge_offset:
            case_judge_penalty += case_judge_offset[(c_id, j_id)] * x[key]
    
    # Use weight differences to ensure proper prioritization
    # Priority: schedule length >> case-judge consistency > room stability > start time
    schedule_length_weight = 1000000
    case_consistency_weight = 1000
    room_stability_weight = 10
    start_time_weight = 1
    
    problem += (
        schedule_length_weight * max_day_used + 
        case_consistency_weight * case_judge_penalty +
        room_stability_weight * room_diversity_penalty + 
        start_time_weight * start_time_penalty,
        "Minimize_Schedule_Length_Case_Consistency_Room_Diversity_And_Early_Start"
    )
    
    # Solve the problem
    print("Solving the ILP model...")
    start_time = time.time()

    # Find available solvers
    available_solvers = pulp.listSolvers(onlyAvailable=True)
    print("Available solvers:", available_solvers)

    # Configure solver with optimality gap and node limit
    solver = None
    if 'COIN_CMD' in available_solvers or 'PULP_CBC_CMD' in available_solvers:
        # Use CBC solver with specific parameters
        solver = pulp.PULP_CBC_CMD(
            gapRel=gap_rel,
            timeLimit=time_limit,
            msg=1  # Show solver output
        )
        print(f"Using CBC solver with gap tolerance {gap_rel*100}% and time limit {time_limit}s")
    elif 'GLPK_CMD' in available_solvers:
        solver = pulp.GLPK_CMD(
            timeLimit=time_limit,
            msg=1
        )
        print(f"Using GLPK solver with time limit {time_limit}s")
    
    if solver:
        problem.solve(solver)
    elif available_solvers:
        problem.solve()  # PuLP will use the first available solver
    else:
        print("No solvers available!")
        return Schedule(work_days, minutes_in_a_work_day, granularity)

    solution_time = time.time() - start_time
    print(f"ILP solved in {solution_time:.2f} seconds with status: {pulp.LpStatus[problem.status]}")

    schedule = Schedule(work_days, minutes_in_a_work_day, granularity, judges=judges, rooms=rooms, meetings=meetings, cases=cases)

    # Extract solution
    if problem.status == pulp.LpStatusOptimal:
        print("Feasible solution found!")
        
        # Extract assignments
        for key, var in x.items():
            val = pulp.value(var)
            if val is not None and val > 0.5:  # If assignment is 1
                m_id, j_id, r_id, d, start_t = key
                
                # Find the corresponding objects
                meeting = next(m for m in meetings if m.meeting_id == m_id)
                judge = next(j for j in judges if j.judge_id == j_id)
                room = next(r for r in rooms if r.room_id == r_id)
                
                duration_slots = meeting_duration_slots[m_id]
                
                # Create appointments for all time slots of this meeting
                for slot_offset in range(duration_slots):
                    appointment = Appointment(
                        meeting=meeting,
                        judge=judge,
                        room=room,
                        day=d,
                        timeslot_in_day=start_t + slot_offset
                    )
                    schedule.add_meeting_to_schedule(appointment)
    else:
        print(f"No feasible solution found. Status: {pulp.LpStatus[problem.status]}")

    return schedule