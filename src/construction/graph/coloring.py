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

##Legacy color finder##
# def get_lowest_available_color(graph: UndirectedGraph, vertex: int) -> int:
#     """
#     Find the lowest color not used by any neighbor of the vertex.
    
#     Args:
#         graph: The undirected graph
#         vertex: The vertex to find a color for
        
#     Returns:
#         The lowest available color index
#     """
#     color_used = [False] * graph.get_num_nodes()  # Initialize all colors as unused
    
#     # Mark colors used by neighbors
#     for neighbor in graph.get_neighbors(vertex):
#         color = graph.get_node(neighbor).get_color()
#         if color != -1:
#             color_used[color] = True
    
#     # Find the lowest unused color
#     for color in range(graph.get_num_nodes()):
#         if not color_used[color]:
#             return color
    
#     # This should never happen as we have at most n nodes and n colors
#     return -1

def find_start_of_chain(graph: UndirectedGraph, vertex: int) -> int:
    """
    Find the vertex ID of the start node of a chain.
    
    Args:
        graph: The undirected graph
        vertex: The vertex index to find the chain for
        
    Returns:
        The index of the first node in the chain
    """
    node: MeetingJudgeRoomNode = graph.get_node(vertex)
    
    meeting_id = node.get_meeting().meeting_id
    judge_id = node.get_judge().judge_id
    room_id = node.get_room().room_id
    
    # Find all vertices in this chain of meetings
    chain_vertices = []
    for i in range(graph.get_num_nodes()):
        check_node = graph.get_node(i)
        if isinstance(check_node, MeetingJudgeRoomNode):
            if (check_node.get_meeting().meeting_id == meeting_id and 
                check_node.get_judge().judge_id == judge_id and
                check_node.get_room().room_id == room_id):
                parts = check_node.identifier.split(",")
                if len(parts) > 1:
                    meeting_number = int(parts[1])
                    chain_vertices.append((i, meeting_number))
    
    # Sort by meeting number (numerically) and return the index of the first node
    if chain_vertices:
        chain_vertices.sort(key=lambda x: x[1])
        return chain_vertices[0][0]
    
    # If no chain found meeting is only 1 timeslot long
    return vertex
       
def color_all_meetings_in_chain(graph: UndirectedGraph, start_vertex: MeetingJudgeRoomNode):
    """
    Color all vertices in a chain consecutively, starting from the given vertex.
    Uses the lowest possible starting color that doesn't conflict with neighbors.
    
    Args:
        graph: The undirected graph
        start_vertex: The first vertex of the chain to color
    """
    # Get meeting, judge, and room IDs to identify all nodes in this chain
    meeting_id = start_vertex.get_meeting().meeting_id
    judge_id = start_vertex.get_judge().judge_id
    room_id = start_vertex.get_room().room_id
    
    # Find all vertices in the chain
    chain_vertices = []
    
    for i in range(graph.get_num_nodes()):
        node = graph.get_node(i)
        if isinstance(node, MeetingJudgeRoomNode):
            # Check if this node is part of the same chain
            if (node.get_meeting().meeting_id == meeting_id and 
                node.get_judge().judge_id == judge_id and
                node.get_room().room_id == room_id):
                # Extract the meeting number from the identifier
                parts = node.identifier.split(",")
                if len(parts) > 1:
                    meeting_number = int(parts[1])
                    chain_vertices.append((i, meeting_number))
    
    # Sort chain vertices by their meeting number (numerically)
    chain_vertices.sort(key=lambda x: x[1])
    chain_indices = [idx for idx, _ in chain_vertices]
    
    if not chain_indices:
        print(f"Warning: No vertices found for chain with meeting_id={meeting_id}, judge_id={judge_id}, room_id={room_id}")
        return
    
    # For each potential starting color, check if it works for the entire chain
    start_color = 0
    valid_start_found = False
    
    while not valid_start_found:
        valid_start_found = True
        
        # Check if this starting color works for all positions in the chain
        for i, vertex_idx in enumerate(chain_indices):
            current_color = start_color + i
            
            # Check if any neighbor conflicts with this color
            for neighbor in graph.get_neighbors(vertex_idx):
                neighbor_color = graph.get_node(neighbor).get_color()
                if neighbor_color == current_color:
                    # Conflict found - this starting color won't work
                    valid_start_found = False
                    start_color += 1
                    break
            
            if not valid_start_found:
                break
    
    # Color the chain consecutively with the found starting color
    for i, vertex_idx in enumerate(chain_indices):
        graph.get_node(vertex_idx).set_color(start_color + i)
        

def DSatur(graph: UndirectedGraph) -> None:
    """
    Apply the DSatur algorithm to color the graph.
    The DSatur algorithm colors vertices in order of their saturation degree.
    
    Args:
        graph: The undirected graph to color
    
    Returns:
        None: Modifies the graph in place using set_color()
    """
    # Initialize all nodes to have no color
    for i in range(graph.get_num_nodes()):
        graph.get_node(i).set_color(-1)
    
    # Track which chains have been colored
    colored_chains = set()  # set of (meeting_id, judge_id, room_id) tuples
    
    # Color nodes one by one
    while True:
        # Select node with highest saturation degree
        node_idx = get_next_node(graph)
        if node_idx == -1:
            break  # All vertices are colored
        
        node = graph.get_node(node_idx)
        
        if isinstance(node, MeetingJudgeRoomNode):
            # Create a chain identifier
            chain_id = (node.get_meeting().meeting_id, node.get_judge().judge_id, node.get_room().room_id)
            
            # If this chain hasn't been colored yet
            if chain_id not in colored_chains:
                # Find the start of the chain
                start_idx = find_start_of_chain(graph, node_idx)
                start_vertex = graph.get_node(start_idx)
                
                # Color all meetings in the chain
                color_all_meetings_in_chain(graph, start_vertex)
                
                # Mark this chain as colored
                colored_chains.add(chain_id)