from collections import deque
from typing import List, Optional
from collections import deque
from warnings import warn

from src.construction.graph.graph import DirectedGraph, JudgeNode, MeetingNode, RoomNode, MeetingJudgeNode, MeetingJudgeRoomNode

class AugmentingPath:
    """Represents an augmenting path in the Ford-Fulkerson algorithm."""
    
    def __init__(self, judge_node: int = -1, case_node: int = -1, 
                 room_node: int = -1, flow: int = 0):
        self.judge_node = judge_node
        self.case_node = case_node
        self.room_node = room_node
        self.flow = flow

def find_augmenting_path(graph: DirectedGraph, source: int, sink: int) -> Optional[List[int]]:
    """Find an augmenting path from source to sink using BFS."""
    parent = [-1] * graph.get_num_nodes()
    visited = [False] * graph.get_num_nodes()
    queue = deque([source])
    visited[source] = True
    
    while queue:
        current = queue.popleft()
        
        # Explore all neighbors with residual capacity
        for neighbor, edge in graph.get_adj_list()[current].items():
            if not visited[neighbor] and edge.get_capacity() > edge.get_flow():
                parent[neighbor] = current
                visited[neighbor] = True
                queue.append(neighbor)
                
                if neighbor == sink:
                    return parent
    
    # No path found
    return None

def update_flow_along_path(graph: DirectedGraph, parent: List[int], source: int, sink: int, path_flow: int) -> None:
    """
    Update flow along the augmenting path.
    
    Returns:
        A tuple of (case_node_id, judge_node_id) if identified in the path
    """
    current = sink
    
    while current != source:
        previous = parent[current]
    
        # Update forward edge - increase flow
        forward_edge = graph.get_edge(previous, current)
        forward_edge.set_flow(forward_edge.get_flow() + path_flow)

        # Update backward edge - decrease flow
        backward_edge = graph.get_edge(current, previous)
        backward_edge.set_flow(backward_edge.get_flow() - path_flow)
        
        current = previous
    

def calculate_bottleneck_capacity(graph: DirectedGraph, parent: List[int], source: int, sink: int) -> int:
    """Calculate the bottleneck capacity of the augmenting path."""
    path_flow = float('inf')
    current = sink
    
    while current != source:
        previous = parent[current]
        edge = graph.get_edge(previous, current)
        path_flow = min(path_flow, edge.get_capacity() - edge.get_flow())
        current = previous
    
    return path_flow


def ford_fulkerson(graph: DirectedGraph, source: int, sink: int) -> int:
    """
    Run the Ford-Fulkerson algorithm to find maximum flow.
    Only updates flow in the graph without recording assignments.
    
    Args:
        graph: The directed graph with residual edges
        source: Source node index
        sink: Sink node index
    """
    total_flow = 0
    # Run Ford-Fulkerson algorithm without recording assignments
    while True:
        # Find an augmenting path
        parent = find_augmenting_path(graph, source, sink)
        
        # If no path found, we've reached maximum flow
        if parent is None:
            break
        
        # Calculate bottleneck capacity
        path_flow = calculate_bottleneck_capacity(graph, parent, source, sink)
        
        # Update flow along the path (don't record assignments yet)
        update_flow_along_path(graph, parent, source, sink, path_flow)
        total_flow += path_flow
        
    return total_flow


def extract_case_judge_assignments(graph: DirectedGraph) -> List[MeetingJudgeNode]:
    """
    Extract final judge-case assignments from the graph after Ford-Fulkerson completes.
    
    Args:
        graph: The directed graph with flow values set
        
    Returns:
        List of CaseJudgeNode objects representing the final assignments
    """
    assigned_pairs = []
    
    # Look at each case node
    for meeting_id in range(1, graph.num_cases + 1):
        meeting_node: MeetingNode = graph.get_node(meeting_id)
        assigned = False

        # Find the judge this case is assigned to
        for judge_id in range(graph.num_cases + 1, graph.num_cases + graph.num_judges + 1):
            edge = graph.get_edge(meeting_id, judge_id)
            
            # If this edge has positive flow, it's a final assignment
            if edge and edge.get_flow() > 0:
                judge_node: JudgeNode = graph.get_node(judge_id)
                pair = MeetingJudgeNode(
                    f"jm_{meeting_id}_{judge_node.get_judge().judge_id}",
                    meeting_node.get_meeting(),
                    judge_node.get_judge()
                )
                assigned_pairs.append(pair)
                assigned = True
                break  # Each case has exactly one judge
        
        if not assigned:
            print(f"Warning: Meeting {meeting_node.get_meeting().meeting_id} was not assigned!")
    
    return assigned_pairs


def assign_cases_to_judges(graph: DirectedGraph) -> List[MeetingJudgeNode]:
    """
    Assign judges to cases using Ford-Fulkerson algorithm with residual graph.
    Extracts final assignments after algorithm completes.
    
    Args:
        graph: The directed graph with residual edges
        
    Returns:
        List of CaseJudgeNode objects representing the judge-case pairs
    """
    source = 0
    sink = graph.get_num_nodes() - 1

    max_flow = ford_fulkerson(graph, source, sink)
    
    # Step 1: Run the Ford-Fulkerson algorithm
    if max_flow != graph.num_cases:
        warn(f"Not all cases could be assigned judges.Found {max_flow} assignments, needed {graph.num_cases}.", RuntimeWarning)
    
    # Step 2: Extract the final assignments from the flow network
    assigned_pairs = extract_case_judge_assignments(graph)
    
    return assigned_pairs




def extract_c_j_room_assignments(graph: DirectedGraph) -> List[MeetingJudgeRoomNode]:
    """
    Extract final judge-case assignments from the graph after Ford-Fulkerson completes.
    
    Args:
        graph: The directed graph with flow values set
        
    Returns:
        List of CaseJudgeNode objects representing the final assignments
    """
    assigned_meetings = []
    
    # Look at each case-judge pair node
    for jm_pair_id in range(1, graph.num_jm_pairs + 1):
        jm_pair_node: MeetingJudgeNode = graph.get_node(jm_pair_id)
        assigned = False
        
        # Find the room this judge-case pair is assigned to
        for room_id in range(graph.num_jm_pairs + 1, graph.num_jm_pairs + graph.num_rooms + 1):
            edge = graph.get_edge(jm_pair_id, room_id)
            
            # If this edge has positive flow, it's a final assignment
            if edge and edge.get_flow() > 0:
                room_node: RoomNode = graph.get_node(room_id)
                pair = MeetingJudgeRoomNode(
                    f"jmr_{jm_pair_node.get_meeting().meeting_id}_{jm_pair_node.get_judge().judge_id}_{room_node.get_room().room_id}",
                    jm_pair_node.get_meeting(),
                    jm_pair_node.get_judge(),
                    room_node.get_room()
                )
                assigned_meetings.append(pair)
                assigned = True
                break
        if not assigned:
            print(f"Warning: Meeting {jm_pair_node.get_meeting().meeting_id} was not assigned!")
            
    return assigned_meetings
        
    

def assign_meeting_judge_pairs_to_rooms(graph: DirectedGraph) -> List[MeetingJudgeRoomNode]:
    """
    Assign rooms to judge-case pairs using the Ford-Fulkerson algorithm.
    This is the second step of the two-step approach.
    
    Args:
        graph: The directed graph prepared for room assignments
        
    Returns:
        List of CaseJudgeRoomNode objects representing the complete assignments
    """
    source = 0
    sink = graph.get_num_nodes() - 1
    
    max_flow = ford_fulkerson(graph, source, sink)
    
    # Step 1: Run the Ford-Fulkerson algorithm
    if max_flow != graph.num_meetings:
        raise RuntimeError(f"Not all judge-case pairs could be assigned rooms. "
                         f"Found {max_flow} assignments, needed {graph.num_meetings}.")
    
    # Step 2: Extract the final assignments from the flow network
    assigned_meetings = extract_c_j_room_assignments(graph)
    
    return assigned_meetings