import math
from collections import defaultdict
from typing import List, Dict, Optional, Type, Set

from src.models import Judge, Meeting, Room, Sagstype, judge_has_skill, calculate_all_judge_capacities

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
    """Node representing a meeting."""
    
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
    """Node representing a meeting-judge assignment."""
    
    def __init__(self, identifier: str, meeting: Meeting, judge: Judge):
        super().__init__(identifier)
        self.meeting = meeting
        self.judge = judge
    
    def get_meeting(self):
        return self.meeting
    
    def get_judge(self):
        return self.judge


class MeetingJudgeRoomNode(Node):
    """Node representing a meeting-judge-room assignment."""
    
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
        self.num_meetings = 0
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
    
    def get_meeting_nodes(self) -> List[MeetingNode]:
        """Get all meeting nodes in the graph."""
        return [node for node in self.nodes if isinstance(node, MeetingNode)]
    
    def add_edge(self, from_id: int, to_id: int, capacity: int) -> None:
        """Add a directed edge to the graph."""
        if not (0 <= from_id < len(self.nodes) and 0 <= to_id < len(self.nodes)):
            raise ValueError(f"Invalid node id: from={from_id}, to={to_id}, nodes={len(self.nodes)}")
        
        self.edges.append(Edge(from_id, to_id, capacity))
        self.adj_list[from_id][to_id] = self.edges[-1]  # Store reference to the edge
    
    def get_edge(self, from_id: int, to_id: int) -> Optional[Edge]:
        """Get an edge by its source and destination node IDs."""
        if not (0 <= from_id < len(self.nodes) and 0 <= to_id < len(self.nodes)):
            raise ValueError(f"Invalid node id: from={from_id}, to={to_id}, nodes={len(self.nodes)}")
        
        return self.adj_list[from_id][to_id]
    
    def initialize_judge_case_graph(self, meetings: List[Meeting], judges: List[Judge]) -> None:
        """Initialize a graph for assigning judges to meetings."""
        # Set counts
        self.num_meetings = len(meetings)
        self.num_judges = len(judges)
        
        # Create source node
        source_node = Node("source")
        source_id = self.add_node(source_node)
        
        # Create meeting nodes and store their node IDs
        meeting_ids = []
        for meeting in meetings:
            meeting_node = MeetingNode(f"meeting_{meeting.meeting_id}", 1, meeting)
            meeting_id = self.add_node(meeting_node)
            meeting_ids.append(meeting_id)
        
        # Create judge nodes and store their node IDs
        judge_node_ids = []
        for judge in judges:
            judge_node = JudgeNode(f"judge_{judge.judge_id}", judge)
            judge_node_id = self.add_node(judge_node)
            judge_node_ids.append(judge_node_id)
        
        # Create sink node
        sink_node = Node("sink")
        sink_id = self.add_node(sink_node)
        
        # Create edges from source to each meeting with capacity 1
        for meeting_id in meeting_ids:
            self.add_edge(source_id, meeting_id, 1)
        
        # Create edges from each meeting to each compatible judge with capacity 1
        for meeting_id, meeting in zip(meeting_ids, meetings):
            for judge_node_id, judge in zip(judge_node_ids, judges):
                if judge_has_skill(judge, meeting.meeting_sagstype):
                    self.add_edge(meeting_id, judge_node_id, 1)
        
        # Create edges from each judge to the sink with balanced capacity
        judge_capacities = calculate_all_judge_capacities(meetings, judges)
        for judge_node_id, judge in zip(judge_node_ids, judges):
            judge_capacity = judge_capacities[judge.judge_id]
            self.add_edge(judge_node_id, sink_id, judge_capacity)
    
    
    def initialize_jm_graph(self, jm_pairs: List[MeetingJudgeNode], rooms: List[Room]) -> None:
        """Initialize a graph for assigning rooms to judge-meeting pairs."""
        # Set counts
        self.num_meetings = len(jm_pairs)
        self.num_rooms = len(rooms)
        
        # Create source node
        source_node = Node("source")
        source_id = self.add_node(source_node)
        
        # Create room nodes and store their IDs
        room_ids = []
        for room in rooms:
            room_node = RoomNode(f"room_{room.room_id}", room)
            room_id = self.add_node(room_node)
            room_ids.append(room_id)
        
        # Create meeting-judge pair nodes and store their IDs
        jm_pair_ids = []
        for jm_pair in jm_pairs:
            jm_node = MeetingJudgeNode(
                f"jm_{jm_pair.get_meeting().meeting_id}_{jm_pair.get_judge().judge_id}", 
                jm_pair.get_meeting(), 
                jm_pair.get_judge()
            )
            jm_pair_id = self.add_node(jm_node)
            jm_pair_ids.append(jm_pair_id)
        
        # Create sink node
        sink_node = Node("sink")
        sink_id = self.add_node(sink_node)
        
        # Create edges from source to room nodes
        for room_id in room_ids:
            # Calculate room capacity based on even distribution
            capacity = math.ceil(self.num_meetings / self.num_rooms)
            self.add_edge(source_id, room_id, capacity)
        
        # Create edges from rooms to meeting-judge pairs
        for room_id in room_ids:
            for jm_pair_id in jm_pair_ids:
                self.add_edge(room_id, jm_pair_id, 1)
        
        # Create edges from meeting-judge pairs to sink
        for jm_pair_id in jm_pair_ids:
            self.add_edge(jm_pair_id, sink_id, 1)
    
    def visualize(self) -> None:
        """Visualize the graph structure."""
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
            # Check for meeting node
            elif isinstance(node, MeetingNode):
                m = node.get_meeting()
                print(f"Meeting (ID: {m.meeting_id}, Duration: {m.meeting_duration}, "
                    f"Sagstype: {m.meeting_sagstype}, Virtual: {m.meeting_virtual})")
            # Check for judge-room node
            elif isinstance(node, JudgeRoomNode):
                j = node.get_judge()
                r = node.get_room()
                skills_str = ", ".join(str(skill) for skill in j.judge_skills)
                print(f"Judge-Room (Judge ID: {j.judge_id}, Virtual: {j.judge_virtual}, "
                    f"Skills: [{skills_str}], Room ID: {r.room_id}, "
                    f"Virtual: {r.room_virtual})")
            # Check for meeting-judge-room node
            elif isinstance(node, MeetingJudgeRoomNode):
                m = node.get_meeting()
                j = node.get_judge()
                r = node.get_room()
                print(f"Meeting-Judge-Room (Meeting ID: {m.meeting_id}, "
                    f"Judge ID: {j.judge_id}, Room ID: {r.room_id})")
            # Check for judge node
            elif isinstance(node, JudgeNode):
                j = node.get_judge()
                print(f"Judge Node (Judge ID: {j.judge_id})")
            # Check for room node
            elif isinstance(node, RoomNode):
                r = node.get_room()
                print(f"Room Node (Room ID: {r.room_id})")
            # Check for meeting-judge node
            elif isinstance(node, MeetingJudgeNode):
                m = node.get_meeting()
                j = node.get_judge()
                print(f"Meeting-Judge Node (Meeting ID: {m.meeting_id}, Judge ID: {j.judge_id})")
            # Check for sink node
            elif node.get_identifier() == "sink":
                print("Sink Node")
            # Fall back to generic node label
            else:
                print(f"Generic Node: {node.get_identifier()}")
        
        # Print edges
        print("\nEdges:")
        print("------")
        if len(self.edges) <= 50:  # Only print all edges for small graphs
            for edge in self.edges:
                from_node = self.nodes[edge.get_from()]
                to_node = self.nodes[edge.get_to()]
                print(f"{edge.get_from()} ({from_node.get_identifier()}) -> {edge.get_to()} ({to_node.get_identifier()}) "
                    f"(Capacity: {edge.get_capacity()}, Flow: {edge.get_flow()})")
        else:
            print(f"[Too many edges to display ({len(self.edges)} edges)]")
            # Show a sample of edges
            print("Sample of edges:")
            for i in range(min(10, len(self.edges))):
                edge = self.edges[i]
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
                print(f"{i} ({node_id}, {len(edges)} outgoing edges) -> ", end="")
                if not edges:
                    print("[]")
                else:
                    print("[ ", end="")
                    for to, edge in edges.items():
                        to_node = self.nodes[to] if to < len(self.nodes) else None
                        to_id = to_node.get_identifier() if to_node else "Unknown"
                        print(f"{to} ({to_id}, cap:{edge.get_capacity()}, flow:{edge.get_flow()}) ", end="")
                    print("]")
        else:
            print(f"[Adjacency list too large to display ({len(self.adj_list)} vertices)]")
            # Show highest-degree vertices
            vertex_degrees = [(i, len(edges)) for i, edges in enumerate(self.adj_list) if i < len(self.nodes)]
            vertex_degrees.sort(key=lambda x: x[1], reverse=True)
            print("Top 10 highest-degree vertices:")
            for i, degree in vertex_degrees[:10]:
                node = self.nodes[i]
                print(f"{i} ({node.get_identifier()}, {degree} outgoing edges)")
        
        # Print flow statistics (if there's flow in the graph)
        if any(edge.get_flow() > 0 for edge in self.edges):
            print("\nFlow Statistics:")
            print("---------------")
            total_flow = sum(edge.get_flow() for edge in self.edges 
                            if self.nodes[edge.get_from()].get_identifier() == "source")
            print(f"Total flow through network: {total_flow}")
            
            # Find flow bottlenecks (edges where flow = capacity)
            bottlenecks = [edge for edge in self.edges 
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
        """Visualize the undirected graph."""
        print("\nUndirected Graph Visualization:")
        print("==============================\n")
        
        # Graph Statistics
        print("Graph Statistics:")
        print("-----------------")
        print(f"Number of vertices: {self.get_num_nodes()}")
        
        total_edges = self.get_num_edges()
        print(f"Number of edges: {total_edges}\n")
        
        # Node Information with Colors
        print("Node Information:")
        print("----------------")
        for i, node in enumerate(self.nodes):
            print(f"Node {i} (Color {node.get_color()}, ID: {node.get_identifier()}): ", end="")
            
            if isinstance(node, MeetingJudgeRoomNode):
                print(f"Meeting {node.get_meeting().meeting_id}, "
                      f"Judge {node.get_judge().judge_id}, "
                      f"Room {node.get_room().room_id}")
            elif isinstance(node, MeetingJudgeNode):
                print(f"Meeting {node.get_meeting().meeting_id}, "
                      f"Judge {node.get_judge().judge_id}")
            elif isinstance(node, JudgeRoomNode):
                print(f"Judge {node.get_judge().judge_id}, "
                      f"Room {node.get_room().room_id}")
            elif isinstance(node, MeetingNode):
                print(f"Meeting {node.get_meeting().meeting_id}")
            elif isinstance(node, JudgeNode):
                print(f"Judge {node.get_judge().judge_id}")
            elif isinstance(node, RoomNode):
                print(f"Room {node.get_room().room_id}")
            else:
                print(node.get_identifier())
        print()
        
        # Adjacency Matrix (truncated for large graphs)
        print("Adjacency Matrix:")
        print("-----------------")
        n_nodes = self.get_num_nodes()
        if n_nodes <= 20:  # Only show full matrix for small graphs
            print("    ", end="")
            for i in range(n_nodes):
                print(f"{i:3} ", end="")
            print("\n    ", end="")
            for i in range(n_nodes):
                print("----", end="")
            print()
            
            for i in range(n_nodes):
                print(f"{i:3}|", end="")
                for j in range(n_nodes):
                    print(f"{self.adj_matrix[i][j]:3} ", end="")
                print(f"  (Color {self.nodes[i].get_color()})")
            print()
        else:
            print(f"[Matrix too large to display ({n_nodes}x{n_nodes})]")
        
        # Edge List with Colors (truncated for large graphs)
        print("Edge List:")
        print("----------")
        if total_edges <= 50:  # Only show all edges for graphs with few edges
            has_edges = False
            for i in range(n_nodes):
                for j in range(i + 1, n_nodes):
                    if self.adj_matrix[i][j] == 1:
                        print(f"{i} (ID: {self.nodes[i].get_identifier()}, Color {self.nodes[i].get_color()}) -- "
                              f"{j} (ID: {self.nodes[j].get_identifier()}, Color {self.nodes[j].get_color()})")
                        has_edges = True
            
            if not has_edges:
                print("No edges in the graph")
        else:
            print(f"[Too many edges to display ({total_edges} edges)]")
            # Show sample of edges
            edge_count = 0
            print("Sample of edges:")
            for i in range(n_nodes):
                for j in range(i + 1, n_nodes):
                    if self.adj_matrix[i][j] == 1:
                        print(f"{i} (ID: {self.nodes[i].get_identifier()}, Color {self.nodes[i].get_color()}) -- "
                              f"{j} (ID: {self.nodes[j].get_identifier()}, Color {self.nodes[j].get_color()})")
                        edge_count += 1
                        if edge_count >= 10:  # Show at most 10 sample edges
                            break
                if edge_count >= 10:
                    break
        print()
        
        # Vertex Degrees and Colors
        print("Vertex Degrees and Colors:")
        print("-------------------------")
        if n_nodes <= 50:  # Only show all vertices for small graphs
            for i in range(n_nodes):
                print(f"Vertex {i} (ID: {self.nodes[i].get_identifier()}): {self.get_degree(i)} connections, "
                      f"Color {self.nodes[i].get_color()}")
        else:
            print(f"[Too many vertices to display ({n_nodes} vertices)]")
            # Show only high-degree vertices
            high_degree_vertices = [(i, self.get_degree(i)) for i in range(n_nodes)]
            high_degree_vertices.sort(key=lambda x: x[1], reverse=True)
            print("Top 10 highest-degree vertices:")
            for i, degree in high_degree_vertices[:10]:
                print(f"Vertex {i} (ID: {self.nodes[i].get_identifier()}): {degree} connections, "
                      f"Color {self.nodes[i].get_color()}")
        print()
    
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