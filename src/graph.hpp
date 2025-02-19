#ifndef graph_hpp
#define graph_hpp

#include <iostream>
#include <memory>
#include <stdexcept>
#include <tuple>
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
    DirectedGraph(int n) : adj_list(n) {
        nodes.reserve(n);
    }

    template <typename NodeType>
    void addNode(const NodeType& node) {
        nodes.push_back(make_unique<NodeType>(node));
    }

    template <typename T>
    T* getNode(int id) {
        return dynamic_cast<T*>(nodes[id].get());
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

    // Add this to the DirectedGraph class in graph.hpp
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
    int n_nodes;
    vector<Edge> edges;
    vector<vector<int>> adj_matrix;
};

#endif