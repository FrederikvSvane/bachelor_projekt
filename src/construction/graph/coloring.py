from typing import List, Set
from src.construction.graph.graph import UndirectedGraph, Node, MeetingJudgeRoomNode

def get_saturation_degree(graph: UndirectedGraph, vertex: int) -> int:
    """
    Calculate the saturation degree of a vertex.
    The saturation degree is the number of different colors used by its neighbors.
    
    Args:
        graph: The undirected graph
        vertex: The vertex to calculate saturation degree for
        
    Returns:
        The saturation degree (number of different colors in the neighbors)
    """
    neighbor_colors = set()
    for neighbor in graph.get_neighbors(vertex):
        color = graph.get_node(neighbor).get_color()
        if color != -1:  # If neighbor is colored
            neighbor_colors.add(color)
    return len(neighbor_colors)
       

def get_next_node(graph: UndirectedGraph) -> int:
    """
    Get the next node to color based on DSatur algorithm.
    The DSatur algorithm chooses the vertex with the highest saturation degree.
    In meeting of a tie, it chooses the vertex with the highest degree.
    
    Args:
        graph: The undirected graph
        
    Returns:
        The index of the next node to color, or -1 if all nodes are colored
    """
    max_sat_degree = -1
    max_degree = -1
    selected_node = -1
    
    for i in range(graph.get_num_nodes()):
        # Skip colored vertices
        if graph.get_node(i).get_color() != -1:
            continue
        
        sat_degree = get_saturation_degree(graph, i)
        degree = graph.get_degree(i)
        
        # Select node with highest saturation degree
        if sat_degree > max_sat_degree:
            max_sat_degree = sat_degree
            max_degree = degree
            selected_node = i
        # If tie in saturation degree, select node with highest degree
        elif sat_degree == max_sat_degree:
            if degree > max_degree:
                max_degree = degree
                selected_node = i
            # If tie in degree, select node with lowest id
            elif degree == max_degree and (selected_node == -1 or i < selected_node):
                selected_node = i
    
    return selected_node


def overlaps(start1: int, end1: int, start2: int, end2: int) -> bool:
    """Check if two time intervals overlap"""
    return start1 < end2 and end1 > start2

def find_valid_timeslot(graph: UndirectedGraph, vertex: int, granularity: int) -> int:
    """Find a valid timeslot that doesn't overlap with neighbors and respects day boundaries"""
    meeting_node = graph.get_node(vertex)
    meeting = meeting_node.get_meeting()
    meeting_length = max(1, meeting.meeting_duration // granularity)
    
    timeslot = 0
    max_attempts = 100_000
    
    for attempt in range(max_attempts):
        # Check day boundary
        day_start = (timeslot // 78) * 78
        day_end = day_start + 78
        
        # If meeting would cross day boundary, move to next valid position
        if timeslot + meeting_length > day_end:
            if day_end - timeslot < meeting_length:
                timeslot = day_end
            else:
                timeslot += 1
            continue
        
        # Check for overlaps with neighbors
        has_conflict = False
        for neighbor_idx in graph.get_neighbors(vertex):
            neighbor_node = graph.get_node(neighbor_idx)
            neighbor_timeslot = neighbor_node.get_color()
            
            if neighbor_timeslot != -1:
                neighbor_meeting = neighbor_node.get_meeting()
                neighbor_length = max(1, neighbor_meeting.meeting_duration // granularity)
                
                if overlaps(timeslot, timeslot + meeting_length, 
                           neighbor_timeslot, neighbor_timeslot + neighbor_length):
                    has_conflict = True
                    break
        
        if not has_conflict:
            return timeslot
        
        timeslot += 1
    
    # If we reach here, we've exhausted max attempts
    # Let's find the highest currently used timeslot and place just after it
    highest_timeslot = 0
    for i in range(graph.get_num_nodes()):
        node = graph.get_node(i)
        if node.get_color() != -1:
            node_meeting = node.get_meeting()
            node_length = max(1, node_meeting.meeting_duration // granularity)
            node_end = node.get_color() + node_length
            highest_timeslot = max(highest_timeslot, node_end)
    
    return highest_timeslot

def DSatur(graph: UndirectedGraph, granularity: int) -> None:
    """Apply the DSatur algorithm to color the graph (optimized version)."""
    # Initialize all nodes to have no color
    for i in range(graph.get_num_nodes()):
        graph.get_node(i).set_color(-1)
    
    # Color nodes one by one
    while True:
        # Select node with highest saturation degree
        node_idx = get_next_node(graph)
        if node_idx == -1:
            break  # All vertices are colored
        
        # Find valid timeslot for this meeting
        timeslot = find_valid_timeslot(graph, node_idx, granularity)
        
        # Set the color (timeslot)
        graph.get_node(node_idx).set_color(timeslot)


def generate_appointments_from_graph(graph: UndirectedGraph, granularity: int) -> List[Node]:
    """Generate appointments from colored graph with expanded timeslots"""
    appointments = []
    
    for i in range(graph.get_num_nodes()):
        node = graph.get_node(i)
        start_timeslot = node.get_color()
        
        if start_timeslot == -1:
            continue
        
        meeting = node.get_meeting()
        judge = node.get_judge()
        room = node.get_room()
        
        # Calculate number of appointments for this meeting
        num_appointments = max(1, meeting.meeting_duration // granularity)
        
        # Create appointments for each timeslot
        for j in range(num_appointments):
            timeslot = start_timeslot + j
            
            # Create a node for each appointment
            node_id = f"meeting_{meeting.meeting_id},{j}"
            appointment_node = MeetingJudgeRoomNode(node_id, meeting, judge, room)
            appointment_node.set_color(timeslot)
            appointments.append(appointment_node)
    
    return appointments