from collections import deque
from typing import List, Dict, Tuple, Optional

from src.model import Case, Judge, Room, Attribute
from src.graph import (
    DirectedGraph, UndirectedGraph, Node, JudgeNode, CaseNode, 
    RoomNode, CaseJudgeNode, CaseJudgeRoomNode, Edge
)

class AugmentingPath:
    """Represents an augmenting path in the Ford-Fulkerson algorithm."""
    
    def __init__(self, judge_node: int = -1, meeting_node: int = -1, 
                 room_node: int = -1, flow: int = 0):
        self.judge_node = judge_node
        self.meeting_node = meeting_node
        self.room_node = room_node
        self.flow = flow


def construct_conflict_graph(assigned_meetings: List[CaseJudgeRoomNode]) -> UndirectedGraph:
    """
    Construct a conflict graph where nodes are meeting-judge-room assignments
    and edges connect assignments that conflict (same judge or same room).
    
    Args:
        assigned_meetings: List of CaseJudgeRoomNode objects representing assignments
        
    Returns:
        An UndirectedGraph representing the conflicts
    """
    conflict_graph = UndirectedGraph()
    
    # Add nodes for each assignment
    for assigned_meeting in assigned_meetings:
        conflict_graph.add_node(assigned_meeting)
    
    # Add edges for conflicts (same judge or same room)
    for i in range(conflict_graph.get_num_nodes()):
        for j in range(conflict_graph.get_num_nodes()):
            if i == j:
                continue
                
            # Get the assignments
            assignment_i = assigned_meetings[i]
            assignment_j = assigned_meetings[j]
            
            # Check if they share a judge or room
            if (assignment_i.get_judge().judge_id == assignment_j.get_judge().judge_id or
                assignment_i.get_room().room_id == assignment_j.get_room().room_id):
                conflict_graph.add_edge(i, j)
    
    return conflict_graph

def bfs(graph: DirectedGraph, source: int, sink: int, parent: List[int]) -> bool:
    """
    Breadth-First Search to find an augmenting path in the residual graph.
    
    Args:
        graph: The directed graph
        source: Source node index
        sink: Sink node index
        parent: List to store the path
        
    Returns:
        True if an augmenting path is found, False otherwise
    """
    num_nodes = graph.get_num_nodes()
    visited = [False] * num_nodes
    queue = deque([source])
    
    # Mark source as visited
    visited[source] = True
    parent[source] = -1
    
    # BFS loop
    while queue:
        current_node = queue.popleft()
        
        # Get neighbors of current node
        adj_list = graph.get_adj_list()
        
        # Process each neighbor with available capacity
        for neighbor_node in list(adj_list[current_node].keys()):
            edge = adj_list[current_node][neighbor_node]
            
            # Check if there's available capacity and node hasn't been visited
            if not visited[neighbor_node] and edge.get_capacity() > edge.get_flow():
                queue.append(neighbor_node)
                visited[neighbor_node] = True
                parent[neighbor_node] = current_node
                
                if neighbor_node == sink:
                    return True  # Path to sink found
    
    return False  # No path to sink found


def assign_cases_to_judges(graph: DirectedGraph) -> List[CaseJudgeNode]:
    """
    Assign judges to cases using a corrected Ford-Fulkerson algorithm implementation.
    Uses an explicit residual graph matrix for better clarity and correctness.
    
    Args:
        graph: The directed graph prepared for judge-case assignments
        
    Returns:
        List of CaseJudgeNode objects representing the judge-case pairs
    """
    # Initialize variables
    source = 0
    sink = graph.get_num_nodes() - 1
    num_nodes = graph.get_num_nodes()
    
    # Create residual capacity matrix
    residual = [[0 for _ in range(num_nodes)] for _ in range(num_nodes)]
    
    # Fill residual graph with initial capacities
    for edge in graph.edges:
        u = edge.get_from()
        v = edge.get_to()
        residual[u][v] = edge.get_capacity()
    
    # Function to find augmenting path using BFS
    def find_augmenting_path():
        parent = [-1] * num_nodes
        visited = [False] * num_nodes
        queue = deque([source])
        visited[source] = True
        
        while queue:
            u = queue.popleft()
            
            for v in range(num_nodes):
                if not visited[v] and residual[u][v] > 0:
                    queue.append(v)
                    visited[v] = True
                    parent[v] = u
                    
                    if v == sink:
                        # Path found
                        return parent
        
        # No path found
        return None
    
    # Ford-Fulkerson algorithm implementation
    max_flow = 0
    assignments = []
    
    while True:
        # Find augmenting path
        parent = find_augmenting_path()
        if parent is None:
            break  # No more augmenting paths
        
        # Calculate path flow (bottleneck capacity)
        path_flow = float('inf')
        v = sink
        
        while v != source:
            u = parent[v]
            path_flow = min(path_flow, residual[u][v])
            v = u
        
        # Update residual capacities
        v = sink
        meeting_node_id = None
        judge_node_id = None
        
        while v != source:
            u = parent[v]
            
            # Identify meeting and judge nodes in this path
            if 1 <= u <= graph.num_meetings:
                meeting_node_id = u
            elif graph.num_meetings < u <= graph.num_meetings + graph.num_judges:
                judge_node_id = u
            
            # Update residual capacities - THIS IS THE KEY FIX
            residual[u][v] -= path_flow  # Forward edge (decrease capacity)
            residual[v][u] += path_flow  # Reverse edge (increase capacity)
            
            v = u
        
        # Record assignment if meeting and judge were identified
        if meeting_node_id is not None and judge_node_id is not None:
            meeting_node = graph.get_node(meeting_node_id)
            judge_node = graph.get_node(judge_node_id)
            
            if meeting_node and judge_node:
                pair = CaseJudgeNode(
                    f"(judge{judge_node.get_judge().judge_id}, case{meeting_node.get_meeting().meeting_id})",
                    meeting_node.get_meeting(),
                    judge_node.get_judge()
                )
                assignments.append(pair)
                
                print(f"Assignment {len(assignments)}: Case "
                      f"{meeting_node.get_meeting().meeting_id} -> Judge "
                      f"{judge_node.get_judge().judge_id}")
        
        max_flow += path_flow
    
    # Verify all cases were assigned
    if max_flow < graph.num_meetings:
        raise RuntimeError(f"\nNot all cases could be assigned judges\n"
                           f"Successfully assigned cases: {max_flow}\n"
                           f"Total amount of cases: {graph.num_meetings}")
    
    return assignments


def assign_case_judge_pairs_to_rooms(graph: DirectedGraph) -> List[CaseJudgeRoomNode]:
    """
    Assign rooms to judge-meeting pairs using the Ford-Fulkerson algorithm.
    This is the second step of the two-step approach.
    
    Args:
        graph: The directed graph prepared for room assignments
        
    Returns:
        List of CaseJudgeRoomNode objects representing the complete assignments
    """
    source = 0
    sink = graph.get_num_nodes() - 1
    total_flow = 0
    
    parent = [-1] * graph.get_num_nodes()
    assigned_meetings = []
    
    print("\n=== Assigning Rooms to Judge-Case Pairs ===")
    
    # Run Ford-Fulkerson
    while bfs(graph, source, sink, parent):
        # Find bottleneck capacity
        path_flow = float('inf')
        v = sink
        while v != source:
            u = parent[v]
            edge = graph.get_edge(u, v)
            if edge:
                path_flow = min(path_flow, edge.get_capacity() - edge.get_flow())
            v = u
        
        # Extract room and jm-pair nodes from this path
        room_node_id = -1
        jm_node_id = -1
        
        v = sink
        while v != source:
            u = parent[v]
            
            # Check if u is a room node (1 to num_rooms)
            if 1 <= u <= graph.num_rooms:
                room_node_id = u
            
            # Check if v is a jm-pair node (num_rooms+1 to num_rooms+jm_pairs.size())
            if graph.num_rooms < v <= graph.num_rooms + graph.num_meetings:
                jm_node_id = v
            
            # Update flow values
            edge = graph.get_edge(u, v)
            if edge:
                edge.set_flow(edge.get_flow() + path_flow)
                
            v = u
        
        # If we identified both a room and a jm-pair, create an assignment
        if room_node_id != -1 and jm_node_id != -1:
            room_node = graph.get_node(room_node_id, RoomNode)
            jm_node = graph.get_node(jm_node_id, CaseJudgeNode)
            
            if room_node and jm_node:
                assignment = CaseJudgeRoomNode(
                    len(assigned_meetings),  # Use index as ID
                    jm_node.get_case(),
                    jm_node.get_judge(),
                    room_node.get_room()
                )
                assigned_meetings.append(assignment)
                
                print(f"Assignment {len(assigned_meetings)}: Case "
                      f"{jm_node.get_case().meeting_id} -> Judge "
                      f"{jm_node.get_judge().judge_id} -> Room "
                      f"{room_node.get_room().room_id}")
        
        total_flow += path_flow
    
    # Check if all jm-pairs were assigned
    if total_flow < graph.num_meetings:
        raise RuntimeError(f"Not all judge-meeting pairs could be assigned rooms: flow = {total_flow}, "
                          f"pairs = {graph.num_meetings}")
    
    print(f"Total Assignments: {len(assigned_meetings)}")
    print("================================")
    
    return assigned_meetings