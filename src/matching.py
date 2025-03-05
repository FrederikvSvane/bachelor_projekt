from collections import deque
from typing import List, Dict, Tuple, Optional

from src.models import Meeting, Judge, Room, Sagstype
from src.graph import (
    DirectedGraph, UndirectedGraph, Node, JudgeNode, MeetingNode, 
    RoomNode, MeetingJudgeNode, MeetingJudgeRoomNode, Edge
)

class AugmentingPath:
    """Represents an augmenting path in the Ford-Fulkerson algorithm."""
    
    def __init__(self, judge_node: int = -1, meeting_node: int = -1, 
                 room_node: int = -1, flow: int = 0):
        self.judge_node = judge_node
        self.meeting_node = meeting_node
        self.room_node = room_node
        self.flow = flow


def construct_conflict_graph(assigned_meetings: List[MeetingJudgeRoomNode]) -> UndirectedGraph:
    """
    Construct a conflict graph where nodes are meeting-judge-room assignments
    and edges connect assignments that conflict (same judge or same room).
    
    Args:
        assigned_meetings: List of MeetingJudgeRoomNode objects representing assignments
        
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

def extract_path_info(parent: List[int], graph: DirectedGraph, source: int, 
                     sink: int, path_flow: int) -> AugmentingPath:
    """
    Extract the judge, meeting, and room nodes from an augmenting path.
    
    Args:
        parent: List of parent nodes forming the path
        graph: The directed graph
        source: Source node index
        sink: Sink node index
        path_flow: The flow value for this path
        
    Returns:
        AugmentingPath object with the identified nodes and flow
    """
    path = AugmentingPath(flow=path_flow)
    
    # Reconstruct the path from sink to source
    v = sink
    while v != source:
        u = parent[v]
        
        # Identify node types along the path
        
        # Check if u is a judge node (1 to num_judges)
        if 1 <= u <= graph.num_judges:
            path.judge_node = u
        
        # Check if u is a meeting node (num_judges+1 to num_judges+num_meetings)
        elif graph.num_judges < u <= graph.num_judges + graph.num_meetings:
            path.meeting_node = u
        
        # Check if v is a room node (num_judges+num_meetings+1 to num_judges+num_meetings+num_rooms)
        if (graph.num_judges + graph.num_meetings < v <= 
            graph.num_judges + graph.num_meetings + graph.num_rooms):
            path.room_node = v
        
        v = u
    
    return path


def print_augmenting_path(path: AugmentingPath, graph: DirectedGraph, path_num: int) -> None:
    """
    Print detailed information about an augmenting path found by Ford-Fulkerson.
    
    Args:
        path: The augmenting path to print
        graph: The directed graph
        path_num: The sequence number of this path
    """
    print(f"Augmenting Path #{path_num}:")
    print(f"  Flow Amount: {path.flow}")
    
    if path.judge_node != -1:
        judge_node = graph.get_node(path.judge_node, JudgeNode)
        if judge_node:
            judge = judge_node.get_judge()
            skills_str = ", ".join(str(skill) for skill in judge.judge_skills)
            print(f"  Judge: ID={judge.judge_id}, Skills=[{skills_str}]")
    
    if path.meeting_node != -1:
        meeting_node = graph.get_node(path.meeting_node, MeetingNode)
        if meeting_node:
            meeting = meeting_node.get_meeting()
            print(f"  Meeting: ID={meeting.meeting_id}, Duration={meeting.meeting_duration}, "
                  f"Type={meeting.meeting_sagstype}")
    
    if path.room_node != -1:
        room_node = graph.get_node(path.room_node, RoomNode)
        if room_node:
            room = room_node.get_room()
            print(f"  Room: ID={room.room_id}, Virtual={room.room_virtual}")
    
    print("  Path: Source -> ", end="")
    if path.judge_node != -1:
        print(f"Judge({path.judge_node}) -> ", end="")
    if path.meeting_node != -1:
        print(f"Meeting({path.meeting_node}) -> ", end="")
    if path.room_node != -1:
        print(f"Room({path.room_node}) -> ", end="")
    print("Sink")
    print("----------------------------------------")


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


def assign_judges_to_meetings(graph: DirectedGraph) -> List[MeetingJudgeNode]:
    """
    Assign judges to meetings using the Ford-Fulkerson algorithm.
    
    Args:
        graph: The directed graph prepared for judge-meeting assignments
        
    Returns:
        List of MeetingJudgeNode objects representing the judge-meeting pairs
    """
    source = 0
    sink = graph.get_num_nodes() - 1
    total_flow = 0
    assigned_pairs = []
    
    
    # Implement Ford-Fulkerson algorithm to find max flow
    while True:
        # Step 1: Find an augmenting path using BFS
        parent = [-1] * graph.get_num_nodes()
        if not bfs(graph, source, sink, parent):
            break  # No more augmenting paths
        
        # Step 2: Calculate the bottleneck capacity
        path_flow = float('inf')
        current_node = sink
        
        while current_node != source:
            previous_node = parent[current_node]
            edge = graph.get_edge(previous_node, current_node)
            if edge:
                path_flow = min(path_flow, edge.get_capacity() - edge.get_flow())
            current_node = previous_node
        
        # Step 3: Update flow along the path
        current_node = sink
        judge_node_id = -1
        meeting_node_id = -1
        
        # Traverse the path again to update flows and identify nodes
        while current_node != source:
            previous_node = parent[current_node]
            
            # Identify the judge node (using updated indices)
            if graph.num_meetings < previous_node < graph.num_meetings + graph.num_judges + 1:
                judge_node_id = previous_node
            
            # Identify the meeting node (using updated indices)
            if 0 < previous_node <= graph.num_meetings:
                meeting_node_id = previous_node
            
            # Update edge flow
            edge = graph.get_edge(previous_node, current_node)
            if edge:
                edge.set_flow(edge.get_flow() + path_flow)
            
            current_node = previous_node
        
        # Step 4: Record this assignment if we found both a judge and a meeting
        if judge_node_id != -1 and meeting_node_id != -1:
            judge_node = graph.get_node(judge_node_id, JudgeNode)
            meeting_node = graph.get_node(meeting_node_id, MeetingNode)
            
            if judge_node and meeting_node:
                pair = MeetingJudgeNode(
                    f"jm_{meeting_node.get_meeting().meeting_id}_{judge_node.get_judge().judge_id}",
                    meeting_node.get_meeting(),
                    judge_node.get_judge()
                )
                assigned_pairs.append(pair)
                
                print(f"Assignment {len(assigned_pairs)}: Meeting "
                      f"{meeting_node.get_meeting().meeting_id} -> Judge "
                      f"{judge_node.get_judge().judge_id}")
        
        total_flow += path_flow
    
    # Verify we found assignments for all meetings
    if total_flow < graph.num_meetings:
        raise RuntimeError(f"\nNot all meetings could be assigned judges\n"
                           f"Succesfully assgined meetings: {total_flow}\n"
                          f"Total amount of meetings: {graph.num_meetings}")
    
    return assigned_pairs


def assign_rooms_to_jm_pairs(graph: DirectedGraph) -> List[MeetingJudgeRoomNode]:
    """
    Assign rooms to judge-meeting pairs using the Ford-Fulkerson algorithm.
    This is the second step of the two-step approach.
    
    Args:
        graph: The directed graph prepared for room assignments
        
    Returns:
        List of MeetingJudgeRoomNode objects representing the complete assignments
    """
    source = 0
    sink = graph.get_num_nodes() - 1
    total_flow = 0
    
    parent = [-1] * graph.get_num_nodes()
    assigned_meetings = []
    
    print("\n=== Assigning Rooms to Judge-Meeting Pairs ===")
    
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
            jm_node = graph.get_node(jm_node_id, MeetingJudgeNode)
            
            if room_node and jm_node:
                assignment = MeetingJudgeRoomNode(
                    len(assigned_meetings),  # Use index as ID
                    jm_node.get_meeting(),
                    jm_node.get_judge(),
                    room_node.get_room()
                )
                assigned_meetings.append(assignment)
                
                print(f"Assignment {len(assigned_meetings)}: Meeting "
                      f"{jm_node.get_meeting().meeting_id} -> Judge "
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