#ifndef graph_hpp
#define graph_hpp

#include <cmath>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <tuple>
#include <unordered_map>
#include <variant>
#include <vector>

#include "judge.hpp"
#include "meeting.hpp"
#include "node.hpp"
#include "room.hpp"

using namespace std;

class Edge {
  private:
    int from_id;
    int to_id;
    int capacity;
    int flow;

  public:
    Edge(int from, int to, int cap)
        : from_id(from), to_id(to), capacity(cap), flow(0) {}

    int getFrom() const { return from_id; }
    int getTo() const { return to_id; }
    int getCapacity() const { return capacity; }
    void setCapacity(int c) { capacity = c; }
    int getFlow() const { return flow; }
    void setFlow(int f) { flow = f; }
};

// Til max-flow
class DirectedGraph {
  private:
    vector<unique_ptr<Node>> nodes;
    vector<Edge> edges;
    vector<unordered_map<int, Edge*>> adj_list;

  public:
    int num_meetings;
    int num_rooms;
    int num_judges;
    int num_jr_pairs;

    DirectedGraph(int n) : adj_list(n) {
        nodes.reserve(n);
        edges.reserve(n * n);
    }

    template <typename NodeType>
    void addNode(const NodeType& node) {
        nodes.push_back(make_unique<NodeType>(node));
    }

    template <typename T>
    T* getNode(int id) {
        return dynamic_cast<T*>(nodes[id].get());
    }

    vector<MeetingNode*> getMeetingNodes() {
        vector<MeetingNode*> meeting_nodes;
        for (const auto& node : nodes) {
            if (auto* meeting_node = dynamic_cast<MeetingNode*>(node.get())) {
                meeting_nodes.push_back(meeting_node);
            }
        }
        return meeting_nodes;
    }

    void addEdge(int from, int to, int capacity) {
        if (from < 0 || from >= nodes.size() || to < 0 || to >= nodes.size()) {
            throw invalid_argument("Invalid node id");
        } else {
            edges.emplace_back(from, to, capacity);
            adj_list[from][to] = &edges.back(); // We store a pointer to the edge (in edges) in the adjacency list for efficiency and O(1) average baby
        }
    }

    Edge* getEdge(int from, int to) {
        auto& edges_from_node = adj_list[from];           // infers type to be unordered_map<int, Edge*>
        auto it               = edges_from_node.find(to); // hash table lookup (returns an "iterator" which just contains (key, value) or in this case (to, Edge*))
        if (it != edges_from_node.end()) {                // "end" is just an iterator that points to the end of the container. So we ask "if (key, value) is not outside the map, then good"
            return it->second;                            // return the Edge* (value) associated with the iterator (to, Edge*)
        }
        return nullptr; // if the edge doesn't exist, return nullptr
    }

    void initialize_flow_graph(int n_meetings, int n_judges, int n_rooms) {
        num_meetings = n_meetings;
        num_judges   = n_judges;
        num_rooms    = n_rooms;
        num_jr_pairs = n_judges * n_rooms;

        Node source(0);
        addNode(source);

        // meeting nodes (ids: 1 to n_meetings)
        for (int i = 1; i <= n_meetings; ++i) {
            Meeting m(i,1);
            MeetingNode m_node(i, m);
            addNode(m_node);
        }

        // judge-room nodes (ids: n_meetings + 1 to n_meetings + (n_judges * n_rooms))
        for (int i = 1; i <= n_judges; ++i) {
            Judge j(i);
            for (int k = 1; k <= n_rooms; ++k) {
                Room r(k);
                const int node_id = n_meetings + (i - 1) * n_rooms + k;
                JudgeRoomNode judge_room_node(node_id, j, r);
                addNode(judge_room_node);
            }
        }

        // sink node as the last node
        const int sink_id = 1 + n_meetings + (n_judges * n_rooms);
        Node sink(sink_id);
        addNode(sink);

        // edges from source to all meeting nodes
        for (int i = 1; i <= n_meetings; ++i) {
            addEdge(0, i, 1);
        }

        // edges from meeting nodes to judge-room nodes
        const int first_meeting_id    = 1;
        const int last_meeting_id     = n_meetings;
        const int first_judge_room_id = n_meetings + 1;
        const int last_judge_room_id  = sink_id - 1;

        for (int from = first_meeting_id; from <= last_meeting_id; ++from) {
            for (int to = first_judge_room_id; to <= last_judge_room_id; ++to) {
                addEdge(from, to, 1);
            }
        }

        // edges from judge-room nodes to sink
        const int capacity = ceil(static_cast<double>(n_meetings) / (n_judges * n_rooms));
        for (int i = first_judge_room_id; i <= last_judge_room_id; ++i) {
            addEdge(i, sink_id, capacity);
        }
    }

    void initialize_bipartite_graph(int n_meetings, int n_judges, int n_rooms) {
        num_meetings = n_meetings;
        num_judges   = n_judges;
        num_rooms    = n_rooms;
        num_jr_pairs = n_judges * n_rooms;

        // meeting nodes (ids: 1 to n_meetings)
        for (int i = 0; i < n_meetings; ++i) {
            Meeting m(i,1);
            MeetingNode m_node(i, m);
            addNode(m_node);
        }

        // judge-room nodes (ids: n_meetings + 1 to n_meetings + (n_judges * n_rooms))
        for (int i = 0; i < n_judges; ++i) {
            Judge j(i);
            for (int k = 0; k < n_rooms; ++k) {
                Room r(k);
                const int node_id = n_meetings + i * n_rooms + k;
                JudgeRoomNode judge_room_node(node_id, j, r);
                addNode(judge_room_node);
            }
        }

        // edges from meeting nodes to judge-room nodes
        const int first_meeting_id    = 0;
        const int last_meeting_id     = n_meetings - 1;
        const int first_judge_room_id = n_meetings;
        const int last_judge_room_id  = n_meetings + num_jr_pairs - 1;

        for (int from = first_meeting_id; from <= last_meeting_id; ++from) {
            for (int to = first_judge_room_id; to <= last_judge_room_id; ++to) {
                addEdge(from, to, 1);
            }
        }
    }

    void visualize() const {
        cout << "\nGraph Visualization:\n";
        cout << "==================\n\n";

        // Print nodes
        cout << "Nodes:\n";
        cout << "------\n";
        for (size_t i = 0; i < nodes.size(); i++) {
            cout << "Node " << i << ": ";

            // Use dynamic_cast to determine node type
            if (auto* meeting_node = dynamic_cast<MeetingNode*>(nodes[i].get())) {
                cout << "Meeting (ID: " << meeting_node->getMeeting().meeting_id << ")";
            } else if (auto* judge_room_node = dynamic_cast<JudgeRoomNode*>(nodes[i].get())) {
                cout << "Judge-Room (Judge ID: " << judge_room_node->getJudge().judge_id
                     << ", Room ID: " << judge_room_node->getRoom().room_id << ")";
            } else if (auto* meeting_judge_room_node = dynamic_cast<MeetingJudgeRoomNode*>(nodes[i].get())) {
                cout << "Meeting-Judge-Room (Meeting ID: " << meeting_judge_room_node->getMeeting().meeting_id
                     << ", Judge ID: " << meeting_judge_room_node->getJudge().judge_id
                     << ", Room ID: " << meeting_judge_room_node->getRoom().room_id << ")";
            }
            cout << endl;
        }

        // Print edges with detailed information
        cout << "\nEdges:\n";
        cout << "------\n";
        for (const auto& edge : edges) {
            cout << edge.getFrom() << " -> " << edge.getTo()
                 << " (Capacity: " << edge.getCapacity()
                 << ", Flow: " << edge.getFlow() << ")" << endl;
        }

        // Print adjacency list representation
        cout << "\nAdjacency List:\n";
        cout << "--------------\n";
        for (size_t i = 0; i < adj_list.size(); i++) {
            cout << i << " -> ";
            if (adj_list[i].empty()) {
                cout << "[]";
            } else {
                cout << "[ ";
                for (const auto& [to, edge] : adj_list[i]) {
                    cout << to << " (cap:" << edge->getCapacity()
                         << ", flow:" << edge->getFlow() << ") ";
                }
                cout << "]";
            }
            cout << endl;
        }
        cout << endl;
    }
};

/*

0: 0 _ _ _
1: _ _ _




*/

// Til k-coloring
struct UndirectedGraph {
    vector<unique_ptr<Node>> nodes;
    int n_nodes;
    vector<vector<int>> adj_matrix;

    UndirectedGraph(int n) : n_nodes(n) {
        adj_matrix.resize(n, vector<int>(n, 0));
    }

    template <typename NodeType>
    void addNode(const NodeType& node) {
        nodes.push_back(make_unique<NodeType>(node));
    }

    template <typename T>
    T* getNode(int id) const {
        return dynamic_cast<T*>(nodes[id].get());
    }

    void addEdge(int from, int to) {
        if (from < 0 || from >= n_nodes || to < 0 || to >= n_nodes) {
            throw invalid_argument("Invalid vertex indices");
        }
        if (from == to) {
            throw invalid_argument("Self-loops are not allowed");
        }
        adj_matrix[from][to] = adj_matrix[to][from] = 1;
    }

    void removeEdge(int from, int to) {
        if (from < 0 || from >= n_nodes || to < 0 || to >= n_nodes) {
            throw invalid_argument("Invalid vertex indices");
        }
        adj_matrix[from][to] = adj_matrix[to][from] = 0;
    }

    bool hasEdge(int from, int to) const {
        if (from < 0 || from >= n_nodes || to < 0 || to >= n_nodes) {
            throw invalid_argument("Invalid vertex indices");
        }
        return adj_matrix[from][to] == 1;
    }

    vector<int> getNeighbors(int vertex) const {
        if (vertex < 0 || vertex >= n_nodes) {
            throw invalid_argument("Invalid vertex index");
        }
        vector<int> neighbors;
        for (int i = 0; i < n_nodes; i++) {
            if (adj_matrix[vertex][i] == 1) {
                neighbors.push_back(i);
            }
        }
        return neighbors;
    }

    int getDegree(int vertex) const {
        if (vertex < 0 || vertex >= n_nodes) {
            throw invalid_argument("Invalid vertex index");
        }
        int degree = 0;
        for (int i = 0; i < n_nodes; i++) {
            degree += adj_matrix[vertex][i];
        }
        return degree;
    }

    void visualize() const {
        cout << "\nUndirected Graph Visualization:\n";
        cout << "==============================\n\n";

        // Graph Statistics
        cout << "Graph Statistics:\n";
        cout << "-----------------\n";
        cout << "Number of vertices: " << n_nodes << "\n";

        int total_edges = 0;
        for (int i = 0; i < n_nodes; i++) {
            for (int j = i + 1; j < n_nodes; j++) {
                total_edges += adj_matrix[i][j];
            }
        }
        cout << "Number of edges: " << total_edges << "\n\n";

        // Node Information with Colors
        cout << "Node Information:\n";
        cout << "----------------\n";
        for (int i = 0; i < n_nodes; i++) {
            cout << "Node " << i << " (Color " << nodes[i]->getColor() << "): ";
            if (auto* mjr_node = dynamic_cast<MeetingJudgeRoomNode*>(nodes[i].get())) {
                cout << "Meeting " << mjr_node->getMeeting().meeting_id
                     << ", Judge " << mjr_node->getJudge().judge_id
                     << ", Room " << mjr_node->getRoom().room_id;
            }
            cout << "\n";
        }
        cout << "\n";

        // Adjacency Matrix
        cout << "Adjacency Matrix:\n";
        cout << "-----------------\n";
        cout << "    ";
        for (int i = 0; i < n_nodes; i++) {
            cout << setw(3) << i << " ";
        }
        cout << "\n    ";
        for (int i = 0; i < n_nodes; i++) {
            cout << "----";
        }
        cout << "\n";

        for (int i = 0; i < n_nodes; i++) {
            cout << setw(3) << i << "|";
            for (int j = 0; j < n_nodes; j++) {
                cout << setw(3) << adj_matrix[i][j] << " ";
            }
            cout << "  (Color " << nodes[i]->getColor() << ")";
            cout << "\n";
        }
        cout << "\n";

        // Edge List with Colors
        cout << "Edge List:\n";
        cout << "----------\n";
        bool has_edges = false;
        for (int i = 0; i < n_nodes; i++) {
            for (int j = i + 1; j < n_nodes; j++) {
                if (adj_matrix[i][j] == 1) {
                    cout << i << " (Color " << nodes[i]->getColor()
                         << ") -- " << j << " (Color " << nodes[j]->getColor() << ")\n";
                    has_edges = true;
                }
            }
        }
        if (!has_edges) {
            cout << "No edges in the graph\n";
        }
        cout << "\n";

        // Vertex Degrees and Colors
        cout << "Vertex Degrees and Colors:\n";
        cout << "-------------------------\n";
        for (int i = 0; i < n_nodes; i++) {
            cout << "Vertex " << i << ": " << getDegree(i)
                 << " connections, Color " << nodes[i]->getColor() << "\n";
        }
        cout << "\n";

        // Adjacency List Format with Colors
        cout << "Adjacency List:\n";
        cout << "--------------\n";
        for (int i = 0; i < n_nodes; i++) {
            cout << i << " (Color " << nodes[i]->getColor() << ") -> ";
            vector<int> neighbors = getNeighbors(i);
            if (neighbors.empty()) {
                cout << "[]";
            } else {
                cout << "[ ";
                for (int neighbor : neighbors) {
                    cout << neighbor << " (Color " << nodes[neighbor]->getColor() << ") ";
                }
                cout << "]";
            }
            cout << "\n";
        }
        cout << "\n";
    }
};

#endif