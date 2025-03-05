from typing import List, Set
from src.graph import UndirectedGraph, Node

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
    In case of a tie, it chooses the vertex with the highest degree.
    
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


def get_lowest_available_color(graph: UndirectedGraph, vertex: int) -> int:
    """
    Find the lowest color not used by any neighbor of the vertex.
    
    Args:
        graph: The undirected graph
        vertex: The vertex to find a color for
        
    Returns:
        The lowest available color index
    """
    color_used = [False] * graph.get_num_nodes()  # Initialize all colors as unused
    
    # Mark colors used by neighbors
    for neighbor in graph.get_neighbors(vertex):
        color = graph.get_node(neighbor).get_color()
        if color != -1:
            color_used[color] = True
    
    # Find the lowest unused color
    for color in range(graph.get_num_nodes()):
        if not color_used[color]:
            return color
    
    # This should never happen as we have at most n nodes and n colors
    return -1


def DSatur(graph: UndirectedGraph) -> None:
    """
    Apply the DSatur algorithm to color the graph.
    The DSatur algorithm colors vertices in order of their saturation degree.
    
    Args:
        graph: The undirected graph to color
    """
    # Initialize all nodes to have no color
    for i in range(graph.get_num_nodes()):
        graph.get_node(i).set_color(-1)
    
    # Color nodes one by one
    for _ in range(graph.get_num_nodes()):
        # Select node with highest saturation degree
        node = get_next_node(graph)
        if node == -1:
            break  # All vertices are colored
        
        # Find the lowest available color for this node
        color = get_lowest_available_color(graph, node)
        graph.get_node(node).set_color(color)