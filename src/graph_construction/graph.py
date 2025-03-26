from collections import defaultdict
from typing import List, Dict, Optional, Type

from src.base_model.case import Case
from src.base_model.judge import Judge
from src.base_model.room import Room
from src.base_model.meeting import Meeting
from src.base_model.capacity_calculator import calculate_all_judge_capacities, calculate_all_room_capacities
from src.base_model.compatibility_checks import case_judge_compatible, judge_room_compatible, case_room_compatible

class Node:
    """Base class for all node types in the graph."""
    
    def __init__(self, identifier: str):
        self.identifier = identifier  # Meaningful string identifier
        self.color = -1
    
    def set_color(self, color: int) -> None:
        """Set the color of this node."""
        self.color = color
    
    def get_color(self) -> int:
        """Get the color of this node."""
        return self.color
    
    def get_identifier(self) -> str:
        """Get the identifier of this node."""
        return self.identifier


class JudgeNode(Node):
    """Node representing a judge."""
    
    def __init__(self, identifier: str, judge: Judge):
        super().__init__(identifier)
        self.judge = judge
    
    def get_judge(self):
        return self.judge


class MeetingNode(Node):
    """Node representing a case."""
    
    def __init__(self, identifier: str, capacity: int, meeting: Meeting):
        super().__init__(identifier)
        self.capacity = capacity
        self.meeting = meeting
        self.flow = 0
    
    def get_capacity(self):
        return self.capacity
    
    def get_flow(self):
        return self.flow
    
    def set_flow(self, flow):
        self.flow = flow
    
    def get_meeting(self):
        return self.meeting


class RoomNode(Node):
    """Node representing a room."""
    
    def __init__(self, identifier: str, room: Room):
        super().__init__(identifier)
        self.room = room
    
    def get_room(self):
        return self.room


class JudgeRoomNode(Node):
    """Node representing a judge-room pair."""
    
    def __init__(self, identifier: str, judge: Judge, room: Room):
        super().__init__(identifier)
        self.judge = judge
        self.room = room
    
    def get_judge(self):
        return self.judge
    
    def get_room(self):
        return self.room


class MeetingJudgeNode(Node):
    """Node representing a case-judge assignment."""
    
    def __init__(self, identifier: str, meeting: Meeting, judge: Judge):
        super().__init__(identifier)
        self.meeting = meeting
        self.judge = judge
    
    def get_meeting(self):
        return self.meeting
    
    def get_judge(self):
        return self.judge


class MeetingJudgeRoomNode(Node):
    """Node representing a case-judge-room assignment."""
    
    def __init__(self, identifier: str, meeting: Meeting, judge: Judge, room: Room):
        super().__init__(identifier)
        self.meeting = meeting
        self.judge = judge
        self.room = room
    
    def get_meeting(self):
        return self.meeting
    
    def get_judge(self):
        return self.judge
    
    def get_room(self):
        return self.room


class Edge:
    """Edge class for the directed graph implementation."""
    
    def __init__(self, from_id: int, to_id: int, capacity: int):
        self.from_id = from_id
        self.to_id = to_id
        self.capacity = capacity
        self.flow = 0
    
    def get_from(self) -> int:
        return self.from_id
    
    def get_to(self) -> int:
        return self.to_id
    
    def get_capacity(self) -> int:
        return self.capacity
    
    def set_capacity(self, capacity: int) -> None:
        self.capacity = capacity
    
    def get_flow(self) -> int:
        return self.flow
    
    def set_flow(self, flow: int) -> None:
        self.flow = flow


class DirectedGraph:
    def __init__(self):
        """Initialize a directed graph with dynamic node tracking."""
        self.nodes = []  # List to store nodes
        self.edges = []  # List to store edges
        self.node_id_map = {}  # Maps node objects to their indices
        self.adj_list = []  # Adjacency list (will be populated as nodes are added)
        self.num_cases = 0
        self.num_rooms = 0
        self.num_judges = 0
        self.num_jr_pairs = 0
        self.num_jm_pairs = 0
        
    def get_adj_list(self) -> List[Dict[int, Edge]]:
        """Get the adjacency list of the graph."""
        return self.adj_list
    
    def add_node(self, node: Node) -> int:
        """
        Add a node to the graph and return its index.
        """
        node_id = len(self.nodes)
        self.nodes.append(node)
        self.node_id_map[node] = node_id
        
        # Extend adjacency list
        while len(self.adj_list) <= node_id:
            self.adj_list.append(defaultdict(lambda: None))
            
        return node_id
    
    def get_node(self, node_id: int, node_type: Type = None):
        """
        Get a node by its ID, optionally cast to a specific type.
        
        Args:
            node_id: The ID of the node to retrieve
            node_type: Optional class to attempt to cast the node to
            
        Returns:
            The node if found and of the requested type, otherwise None
        """
        if 0 <= node_id < len(self.nodes):
            node = self.nodes[node_id]
            if node_type is None or isinstance(node, node_type):
                return node
        return None
    
    def get_num_nodes(self) -> int:
        """Get the number of nodes in the graph."""
        return len(self.nodes)
    
    def get_case_nodes(self) -> List[MeetingNode]:
        """Get all case nodes in the graph."""
        return [node for node in self.nodes if isinstance(node, MeetingNode)]
    
    def add_edge(self, from_id: int, to_id: int, capacity: int) -> None:
        if not (0 <= from_id < len(self.nodes) and 0 <= to_id < len(self.nodes)):
            raise ValueError(f"Invalid node id: from={from_id}, to={to_id}, nodes={len(self.nodes)}")
        
        # Add forward edge
        self.edges.append(Edge(from_id, to_id, capacity))
        self.adj_list[from_id][to_id] = self.edges[-1]  # Store reference to the edge
        
        # Add reverse edge with zero capacity (for residual graph)
        # Only add if it doesn't already exist
        if self.adj_list[to_id].get(from_id) is None:
            self.edges.append(Edge(to_id, from_id, 0))
            self.adj_list[to_id][from_id] = self.edges[-1]
    
    def get_edge(self, from_id: int, to_id: int) -> Optional[Edge]:
        """Get an edge by its source and destination node IDs."""
        if not (0 <= from_id < len(self.nodes) and 0 <= to_id < len(self.nodes)):
            raise ValueError(f"Invalid node id: from={from_id}, to={to_id}, nodes={len(self.nodes)}")
        
        return self.adj_list[from_id][to_id]
    
    def initialize_meeting_to_judge_graph(self, meetings: list[Meeting], judges: List[Judge]) -> None:
        """Initialize a graph for assigning judges to cases."""
        # Set counts
        self.num_cases = len(meetings)
        self.num_judges = len(judges)
        
        # Create source node
        source_node = Node("source")
        source_id = self.add_node(source_node)
        
        # Create case nodes
        meeting_ids = []
        for meeting in meetings:
            meeting_node = MeetingNode(f"meeting_{meeting.meeting_id}", 1, meeting)
            meeting_id = self.add_node(meeting_node)
            meeting_ids.append(meeting_id)
        
        # Create judge nodes
        judge_node_ids = []
        for judge in judges:
            judge_node = JudgeNode(f"judge_{judge.judge_id}", judge)
            judge_node_id = self.add_node(judge_node)
            judge_node_ids.append(judge_node_id)
        
        # Create sink node
        sink_node = Node("sink")
        sink_id = self.add_node(sink_node)
        
        # Create edges from source to each case with capacity 1
        for meeting_id in meeting_ids:
            self.add_edge(source_id, meeting_id, 1)
        
        # Create edges from each case to compatible judges with capacity 1
        for i, meeting_id in enumerate(meeting_ids):
            meeting = meetings[i]
            for j, judge_node_id in enumerate(judge_node_ids):
                judge = judges[j]
                # Use two-directional compatibility checks
                if (case_judge_compatible(meeting.case, judge)):
                    self.add_edge(meeting_id, judge_node_id, 1)
        
        # Create edges from each judge to the sink with balanced capacity
        judge_capacities = calculate_all_judge_capacities(meetings, judges)
        for i, judge_node_id in enumerate(judge_node_ids):
            judge_capacity = judge_capacities[judges[i].judge_id]
            self.add_edge(judge_node_id, sink_id, judge_capacity)

    def initialize_case_judge_pair_to_room_graph(self, jm_pairs: List[MeetingJudgeNode], rooms: List[Room]) -> None:
        """Initialize a graph for assigning rooms to case-judge pairs."""
        # Set counts
        self.num_meetings = len(jm_pairs)
        self.num_rooms = len(rooms)
        self.num_jm_pairs = len(jm_pairs)
        
        # Create source node
        source_node = Node("source")
        source_id = self.add_node(source_node)
        
        # Create case-judge pair nodes and store their IDs
        jm_pair_ids = []
        for jm_pair in jm_pairs:
            jm_node = MeetingJudgeNode(
                f"jm_{jm_pair.get_meeting().meeting_id}_{jm_pair.get_judge().judge_id}", 
                jm_pair.get_meeting(), 
                jm_pair.get_judge()
            )
            jm_pair_id = self.add_node(jm_node)
            jm_pair_ids.append(jm_pair_id)
            
        # Create room nodes and store their IDs
        room_ids = []
        for room in rooms:
            room_node = RoomNode(f"room_{room.room_id}", room)
            room_id = self.add_node(room_node)
            room_ids.append(room_id)
        
        # Create sink node
        sink_node = Node("sink")
        sink_id = self.add_node(sink_node)
        
        # Create edges from source to judge_case pairs
        for jm_pair_id in jm_pair_ids:
            self.add_edge(source_id, jm_pair_id, 1)
        
        # Create edges from judge_case pairs to rooms
        for i, jm_pair_id in enumerate(jm_pair_ids):
            jm_pair = jm_pairs[i]
            judge: Judge = jm_pair.get_judge()
            meeting: Meeting = jm_pair.get_meeting()
            for j, room_id in enumerate(room_ids):
                room: Room = rooms[j]
                if judge_room_compatible(judge, room) and case_room_compatible(meeting.case, room):
                    self.add_edge(jm_pair_id, room_id, 1)
        
        # Create edges from rooms to sink
        room_capacities = calculate_all_room_capacities(jm_pairs, rooms)
        for i, room_id in enumerate(room_ids):
            room_capacity = room_capacities[rooms[i].room_id]
            self.add_edge(room_id, sink_id, room_capacity)
    
    def visualize(self) -> None:
        """Visualize the graph structure with only forward edges."""
        if True:
            print("\nGraph Visualization:")
            print("==================\n")
            
            # Print nodes with additional details
            print("Nodes:")
            print("------")
            for i, node in enumerate(self.nodes):
                print(f"Node {i} (ID: {node.get_identifier()}): ", end="")
                
                # Check for source node
                if node.get_identifier() == "source":
                    print("Source Node")
                # Check for case node
                elif isinstance(node, MeetingNode):
                    m = node.get_meeting()
                    print(f"Case (ID: {m.meeting_id}, Duration: {m.meeting_duration}, Attributes: {m.case.characteristics}, Required: {m.case.judge_requirements})")
                # Check for judge-room node
                elif isinstance(node, JudgeRoomNode):
                    j = node.get_judge()
                    r = node.get_room()
                    characteristics_str = ", ".join(str(attribute) for attribute in j.characteristics)
                    print(f"Judge-Room (Judge ID: {j.judge_id}, Virtual: {j.judge_virtual}, "
                        f"Skills: [{characteristics_str}], Room ID: {r.room_id}, "
                        f"Virtual: {r.room_virtual})")
                # Check for case-judge-room node
                elif isinstance(node, MeetingJudgeRoomNode):
                    m = node.get_meeting()
                    j = node.get_judge()
                    r = node.get_room()
                    print(f"Case-Judge-Room (Case ID: {m.meeting_id}, "
                        f"Judge ID: {j.judge_id}, Room ID: {r.room_id})")
                # Check for judge node
                elif isinstance(node, JudgeNode):
                    j = node.get_judge()
                    print(f"Judge Node (Judge ID: {j.judge_id}), Skills: {j.characteristics}, case_reqs: {j.case_requirements}")
                # Check for room node
                elif isinstance(node, RoomNode):
                    r = node.get_room()
                    print(f"Room Node (Room ID: {r.room_id}, characteristics: {r.characteristics}, judge_reqs: {r.judge_requirements}, case_reqs: {r.case_requirements})")
                # Check for case-judge node
                elif isinstance(node, MeetingJudgeNode):
                    m = node.get_meeting()
                    j = node.get_judge()
                    print(f"Case-Judge Node (Case ID: {m.meeting_id}, Judge ID: {j.judge_id}, case_room_reqs: {m.case.room_requirements}, judge_room_reqs: {j.room_requirements})")
                # Check for sink node
                elif node.get_identifier() == "sink":
                    print("Sink Node")
                # Fall back to generic node label
                else:
                    print(f"Generic Node: {node.get_identifier()}")
            
            # Filter out backward edges for display
            forward_edges = [edge for edge in self.edges if edge.get_capacity() > 0]
            
            # Print edges
            print("\nEdges:")
            print("------")
            if len(forward_edges) <= 50:  # Only print all edges for small graphs
                for edge in forward_edges:
                    from_node = self.nodes[edge.get_from()]
                    to_node = self.nodes[edge.get_to()]
                    print(f"{edge.get_from()} ({from_node.get_identifier()}) -> {edge.get_to()} ({to_node.get_identifier()}) "
                        f"(Capacity: {edge.get_capacity()}, Flow: {edge.get_flow()})")
            else:
                print(f"[Too many edges to display ({len(forward_edges)} edges)]")
                # Show a sample of edges
                print("Sample of edges:")
                for i in range(min(10, len(forward_edges))):
                    edge = forward_edges[i]
                    from_node = self.nodes[edge.get_from()]
                    to_node = self.nodes[edge.get_to()]
                    print(f"{edge.get_from()} ({from_node.get_identifier()}) -> {edge.get_to()} ({to_node.get_identifier()}) "
                        f"(Capacity: {edge.get_capacity()}, Flow: {edge.get_flow()})")
            
            # Print adjacency list
            print("\nAdjacency List:")
            print("--------------")
            if len(self.adj_list) <= 50:  # Only print full list for small graphs
                for i, edges in enumerate(self.adj_list):
                    node = self.nodes[i] if i < len(self.nodes) else None
                    node_id = node.get_identifier() if node else "Unknown"
                    
                    # Filter out backward edges
                    forward_outgoing = {to: edge for to, edge in edges.items() if edge and edge.get_capacity() > 0}
                    
                    print(f"{i} ({node_id}, {len(forward_outgoing)} outgoing edges) -> ", end="")
                    if not forward_outgoing:
                        print("[]")
                    else:
                        print("[ ", end="")
                        for to, edge in forward_outgoing.items():
                            to_node = self.nodes[to] if to < len(self.nodes) else None
                            to_id = to_node.get_identifier() if to_node else "Unknown"
                            print(f"{to} ({to_id}, cap:{edge.get_capacity()}, flow:{edge.get_flow()}) ", end="")
                        print("]")
            else:
                print(f"[Adjacency list too large to display ({len(self.adj_list)} vertices)]")
                # Show highest-degree vertices based on forward edges only
                vertex_degrees = []
                for i, edges in enumerate(self.adj_list):
                    if i < len(self.nodes):
                        # Count only forward edges
                        forward_count = sum(1 for edge in edges.values() if edge and edge.get_capacity() > 0)
                        vertex_degrees.append((i, forward_count))
                
                vertex_degrees.sort(key=lambda x: x[1], reverse=True)
                print("Top 10 highest-degree vertices:")
                for i, degree in vertex_degrees[:10]:
                    node = self.nodes[i]
                    print(f"{i} ({node.get_identifier()}, {degree} outgoing edges)")
            
            # Print flow statistics (if there's flow in the graph)
            if any(edge.get_flow() > 0 for edge in forward_edges):
                print("\nFlow Statistics:")
                print("---------------")
                total_flow = sum(edge.get_flow() for edge in forward_edges 
                                if self.nodes[edge.get_from()].get_identifier() == "source")
                print(f"Total flow through network: {total_flow}")
                
                # Find flow bottlenecks (edges where flow = capacity)
                bottlenecks = [edge for edge in forward_edges 
                            if edge.get_flow() == edge.get_capacity() and edge.get_capacity() > 0]
                if bottlenecks:
                    print("\nBottleneck Edges (Flow = Capacity):")
                    for edge in bottlenecks[:10]:  # Show at most 10 bottlenecks
                        from_node = self.nodes[edge.get_from()]
                        to_node = self.nodes[edge.get_to()]
                        print(f"{edge.get_from()} ({from_node.get_identifier()}) -> "
                            f"{edge.get_to()} ({to_node.get_identifier()}) "
                            f"(Flow/Capacity: {edge.get_flow()}/{edge.get_capacity()})")
                    if len(bottlenecks) > 10:
                        print(f"... and {len(bottlenecks) - 10} more bottleneck edges")
            
            print()

class UndirectedGraph:
    """Undirected graph implementation for graph coloring problems."""
    
    def __init__(self):
        """Initialize an undirected graph with dynamic node tracking."""
        self.nodes = []  # List to store nodes
        self.node_id_map = {}  # Maps node objects to their indices
        self.adj_matrix = []  # Adjacency matrix (will be resized as nodes are added)
    
    def add_node(self, node: Node) -> int:
        """
        Add a node to the graph and return its index.
        
        Args:
            node: The node to add to the graph
            
        Returns:
            The index of the added node
        """
        node_id = len(self.nodes)
        self.nodes.append(node)
        self.node_id_map[node] = node_id
        
        # Extend adjacency matrix with a new row and column
        if self.adj_matrix:
            for row in self.adj_matrix:
                row.append(0)
            self.adj_matrix.append([0] * (node_id + 1))
        else:
            self.adj_matrix = [[0]]
            
        return node_id
    
    def get_node(self, node_id: int, node_type: Type = None):
        """
        Get a node by its ID, optionally cast to a specific type.
        
        Args:
            node_id: The ID of the node to retrieve
            node_type: Optional class to attempt to cast the node to
            
        Returns:
            The node if found and of the requested type, otherwise None
        """
        if 0 <= node_id < len(self.nodes):
            node = self.nodes[node_id]
            if node_type is None or isinstance(node, node_type):
                return node
        return None
    
    def add_edge(self, from_id: int, to_id: int) -> None:
        """
        Add an undirected edge between two nodes.
        
        Args:
            from_id: The ID of the first node
            to_id: The ID of the second node
            
        Raises:
            ValueError: If either node ID is invalid or if attempting to add a self-loop
        """
        if not (0 <= from_id < len(self.nodes) and 0 <= to_id < len(self.nodes)):
            raise ValueError("Invalid vertex indices")
        if from_id == to_id:
            raise ValueError("Self-loops are not allowed")
        
        self.adj_matrix[from_id][to_id] = self.adj_matrix[to_id][from_id] = 1
    
    def remove_edge(self, from_id: int, to_id: int) -> None:
        """
        Remove an edge between two nodes.
        
        Args:
            from_id: The ID of the first node
            to_id: The ID of the second node
            
        Raises:
            ValueError: If either node ID is invalid
        """
        if not (0 <= from_id < len(self.nodes) and 0 <= to_id < len(self.nodes)):
            raise ValueError("Invalid vertex indices")
        
        self.adj_matrix[from_id][to_id] = self.adj_matrix[to_id][from_id] = 0
    
    def has_edge(self, from_id: int, to_id: int) -> bool:
        """
        Check if an edge exists between two nodes.
        
        Args:
            from_id: The ID of the first node
            to_id: The ID of the second node
            
        Returns:
            True if an edge exists, False otherwise
            
        Raises:
            ValueError: If either node ID is invalid
        """
        if not (0 <= from_id < len(self.nodes) and 0 <= to_id < len(self.nodes)):
            raise ValueError("Invalid vertex indices")
        
        return self.adj_matrix[from_id][to_id] == 1
    
    def get_neighbors(self, vertex: int) -> List[int]:
        """
        Get all neighbors of a vertex.
        
        Args:
            vertex: The ID of the vertex
            
        Returns:
            A list of vertex IDs that are adjacent to the given vertex
            
        Raises:
            ValueError: If the vertex ID is invalid
        """
        if not (0 <= vertex < len(self.nodes)):
            raise ValueError("Invalid vertex index")
        
        return [i for i in range(len(self.nodes)) if self.adj_matrix[vertex][i] == 1]
    
    def get_degree(self, vertex: int) -> int:
        """
        Get the degree (number of connections) of a vertex.
        
        Args:
            vertex: The ID of the vertex
            
        Returns:
            The number of edges connected to the vertex
            
        Raises:
            ValueError: If the vertex ID is invalid
        """
        if not (0 <= vertex < len(self.nodes)):
            raise ValueError("Invalid vertex index")
        
        return sum(self.adj_matrix[vertex])
    
    def get_num_nodes(self) -> int:
        """
        Get the number of nodes in the graph.
        
        Returns:
            The total number of nodes
        """
        return len(self.nodes)
    
    def get_num_edges(self) -> int:
        """
        Get the number of edges in the graph.
        
        Returns:
            The total number of edges
        """
        return sum(self.adj_matrix[i][j] for i in range(len(self.nodes)) 
                  for j in range(i + 1, len(self.nodes)))
    
    def visualize(self) -> None:
        if False:
            """Visualize the undirected graph with enhanced chain display."""
            print("\nUndirected Graph Visualization:")
            print("==============================\n")
            
            # Graph Statistics
            print("Graph Statistics:")
            print("-----------------")
            print(f"Number of vertices: {self.get_num_nodes()}")
            total_edges = self.get_num_edges()
            print(f"Number of edges: {total_edges}\n")
            
            # Group nodes by case_id for better visualization of chains
            case_chains = {}
            
            for i, node in enumerate(self.nodes):
                if isinstance(node, CaseJudgeRoomNode):
                    case_id = node.get_case().case_id
                    if case_id not in case_chains:
                        case_chains[case_id] = []
                    case_chains[case_id].append((i, node))
            
            # Display Case Chains
            print("Case Chains:")
            print("------------")
            if case_chains:
                for case_id, nodes in case_chains.items():
                    print(f"Case {case_id} Chain:")
                    # Sort nodes by identifier
                    nodes.sort(key=lambda x: x[1].get_identifier())
                    
                    for idx, node in nodes:
                        identifier = node.get_identifier()
                        judge = node.get_judge().judge_id
                        room = node.get_room().room_id
                        color = node.get_color()
                        print(f"  {identifier} - Judge {judge}, Room {room}, Color {color}")
                    print()
            else:
                print("No case chains found in the graph.\n")
        
        # Case Chain Conflict Analysis
        print("Chain Conflict Analysis:")
        print("-----------------------")
        if False:
            if len(case_chains) > 1:
                case_ids = list(case_chains.keys())
                for i in range(len(case_ids)):
                    for j in range(i+1, len(case_ids)):
                        case_i_id = case_ids[i]
                        case_j_id = case_ids[j]
                        
                        print(f"Conflicts between Case {case_i_id} and Case {case_j_id}:")
                        conflict_found = False
                        
                        for idx_i, node_i in case_chains[case_i_id]:
                            for idx_j, node_j in case_chains[case_j_id]:
                                if self.has_edge(idx_i, idx_j):
                                    conflict_found = True
                                    # Determine conflict reason with specific details
                                    reasons = []
                                    if node_i.get_judge().judge_id == node_j.get_judge().judge_id:
                                        judge_id = node_i.get_judge().judge_id
                                        reasons.append(f"Same Judge (Judge {judge_id})")
                                    if node_i.get_room().room_id == node_j.get_room().room_id:
                                        room_id = node_i.get_room().room_id
                                        reasons.append(f"Same Room (Room {room_id})")
                                    reason_str = ", ".join(reasons) if reasons else "Unknown"
                                    
                                    print(f"  {node_i.get_identifier()} conflicts with {node_j.get_identifier()}: {reason_str}")
                        
                        if not conflict_found:
                            print("  No conflicts found")
                        print()
        
        # Color Summary
        print("Color Usage Summary:")
        print("-------------------")
        if self.is_colored():
            color_counts = self.get_color_counts()
            for color, count in sorted(color_counts.items()):
                print(f"Color {color}: {count} nodes")
            
            if self.is_valid_coloring():
                print("\nThe coloring is valid - no conflicts between same-colored nodes.")
            else:
                print("\nWARNING: Invalid coloring detected!")
        else:
            print("Graph is not fully colored.")
        
        # Original node and edge information for completeness
        if self.get_num_nodes() <= 20:  # Only show detailed adjacency for small graphs
            print("\nAdjacency Matrix:")
            print("-----------------")
            print("    ", end="")
            for i in range(self.get_num_nodes()):
                print(f"{i:3} ", end="")
            print("\n    " + "----" * self.get_num_nodes())
            
            for i in range(self.get_num_nodes()):
                print(f"{i:3}|", end="")
                for j in range(self.get_num_nodes()):
                    print(f"{self.adj_matrix[i][j]:3} ", end="")
                print()
        
        print("\n")
    
    def is_colored(self) -> bool:
        """
        Check if all nodes in the graph are colored.
        
        Returns:
            True if all nodes have a valid color (>= 0), False otherwise
        """
        return all(node.get_color() >= 0 for node in self.nodes)
    
    def is_valid_coloring(self) -> bool:
        """
        Check if the current coloring is valid (no adjacent nodes have the same color).
        
        Returns:
            True if the coloring is valid, False otherwise
        """
        for i in range(len(self.nodes)):
            for j in range(i + 1, len(self.nodes)):
                if (self.adj_matrix[i][j] == 1 and 
                    self.nodes[i].get_color() >= 0 and 
                    self.nodes[j].get_color() >= 0 and 
                    self.nodes[i].get_color() == self.nodes[j].get_color()):
                    return False
        return True
    
    def get_color_counts(self) -> Dict[int, int]:
        """
        Get the count of nodes for each color.
        
        Returns:
            A dictionary mapping color to the number of nodes with that color
        """
        color_counts = {}
        for node in self.nodes:
            color = node.get_color()
            if color >= 0:  # Only count valid colors
                color_counts[color] = color_counts.get(color, 0) + 1
        return color_counts
    
    def reset_colors(self) -> None:
        """Reset the color of all nodes to -1 (uncolored)."""
        for node in self.nodes:
            node.set_color(-1)
            
def construct_conflict_graph(assigned_meetings: List[MeetingJudgeRoomNode], granularity):
    """
    Construct a conflict graph where nodes are case-judge-room assignments
    and edges connect assignments that conflict (same judge or same room).
    
    Args:
        assigned_cases: List of CaseJudgeRoomNode objects representing assignments
        
    Returns:
        An UndirectedGraph representing the conflicts
    """

    conflict_graph = UndirectedGraph()
    all_nodes = []
    node_to_index = {}  # Map to track node objects to their indices
    
    # Dictionary to track all nodes by judge_id and room_id for faster conflict detection
    nodes_by_judge = {}
    nodes_by_room = {}
    
    # Add nodes based on how many timeslots the meeting span
    for assigned_meeting in assigned_meetings:
        length = max(1, assigned_meeting.get_meeting().meeting_duration // granularity)
        
        # Create nodes for each timeslot of this case
        meeting_indices = []
        for i in range(length):
            # Create a node identifier
            node_id = f"meeting_{assigned_meeting.get_meeting().meeting_id},{i}"
            
            # Create a new node for each timeslot with all required parameters
            node = MeetingJudgeRoomNode(node_id, 
                                     assigned_meeting.get_meeting(), 
                                     assigned_meeting.get_judge(), 
                                     assigned_meeting.get_room())
            
            # Add the node and get its index
            index = conflict_graph.add_node(node)
            node_to_index[node] = index  # Store mapping from node to index
            all_nodes.append(node)
            meeting_indices.append(index)
            
            # Track nodes by judge and room for conflict detection
            judge_id = assigned_meeting.get_judge().judge_id
            room_id = assigned_meeting.get_room().room_id
            
            if judge_id not in nodes_by_judge:
                nodes_by_judge[judge_id] = []
            nodes_by_judge[judge_id].append(index)
            
            if room_id not in nodes_by_room:
                nodes_by_room[room_id] = []
            nodes_by_room[room_id].append(index)
        
        # Add edges between all pairs of nodes in this case's chain
        for i in range(len(meeting_indices)):
            for j in range(i+1, len(meeting_indices)):
                conflict_graph.add_edge(meeting_indices[i], meeting_indices[j])
    
    # Add edges for conflicts (same judge or same room)
    # Process conflicts by judge
    for judge_id, indices in nodes_by_judge.items():
        for i in range(len(indices)):
            for j in range(i+1, len(indices)):
                conflict_graph.add_edge(indices[i], indices[j])
    
    # Process conflicts by room
    for room_id, indices in nodes_by_room.items():
        for i in range(len(indices)):
            for j in range(i+1, len(indices)):
                conflict_graph.add_edge(indices[i], indices[j])
    
    return conflict_graph

        