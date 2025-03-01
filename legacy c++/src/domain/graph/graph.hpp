#pragma once

#include <cmath>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <tuple>
#include <unordered_map>
#include <variant>
#include <vector>

#include "../judge.hpp"
#include "../meeting.hpp"
#include "../room.hpp"
#include "../sagstype.hpp"
#include "node.hpp"

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
    int num_jm_pairs;

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

    int getNumNodes() {
        return nodes.size();
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
        auto& edges_from_node = adj_list[from]; // infers type to be unordered_map<int, Edge*>
        auto it               = edges_from_node.find(
            to); // hash table lookup (returns an "iterator" which just contains (key, value) or in this case (to, Edge*))
        if (it !=
            edges_from_node.end()) { // "end" is just an iterator that points to the end of the container. So we ask "if (key, value) is not outside the map, then good"
            return it->second;       // return the Edge* (value) associated with the iterator (to, Edge*)
        }
        return nullptr; // if the edge doesn't exist, return nullptr
    }

    const vector<unordered_map<int, Edge*>> get_adj_list() const {
        return adj_list;
    }

    void initialize_judge_case_graph(const vector<Meeting>& meetings, const vector<Judge>& judges) {
        if (meetings.size() > UINT32_MAX || judges.size() > UINT32_MAX) {
            throw invalid_argument("Too many meetings or judges");
        }
        num_meetings = (int)meetings.size();
        num_judges   = (int)judges.size();

        int next_id = 0;
        Node source(++next_id);
        addNode(source);

        // Create a node for each judge
        for (int i = 0; i < num_judges; i++) {
            JudgeNode judge_node(++next_id, judges[i]);
            addNode(judge_node);
        }

        // Create a node for each meeting
        for (int i = 0; i < num_meetings; i++) {
            MeetingNode meeting_node(++next_id, 1, meetings[i]);
            addNode(meeting_node);
        }

        Node sink(++next_id);
        addNode(sink);
        for (int i = 1; i <= num_judges; i++) {
            int judge_capacity = calculate_judge_capacity(meetings, judges, i);
            addEdge(0, i, judge_capacity);
        }

        // Create edges from each judge to each meeting
        for (int i = 1; i <= num_judges; i++) {
            auto& judge = judges[i - 1];
            for (int j = 1; j <= num_meetings; j++) {
                auto& meeting = meetings[j - 1];

                if (judge_has_skill(judge, meeting.meeting_sagstype)) {
                    addEdge(i, num_judges + j, 1);
                }
            }
        }

        // Create edges from each meeting to the sink
        for (int i = 1; i <= num_meetings; i++) {
            addEdge(num_judges + i, num_judges + num_meetings + 1, 1);
        }
    }

    void initialize_jm_graph(const vector<MeetingJudgeNode>& jm_pairs, const vector<Room>& rooms) {
        if (jm_pairs.size() > UINT32_MAX || rooms.size() > UINT32_MAX) {
            throw invalid_argument("Too many judge-meeting pairs or rooms");
        }
        num_meetings = (int)jm_pairs.size();
        num_rooms    = (int)rooms.size();

        int next_id = 0;
        Node source(++next_id);
        addNode(source);

        // Create a node for each room
        for (int i = 0; i < num_rooms; i++) {
            RoomNode room_node(++next_id, rooms[i]);
            addNode(room_node);
        }

        // Create a node for each meeting-judge pair
        for (int i = 0; i < num_meetings; i++) {
            MeetingJudgeNode jm_node(++next_id, jm_pairs[i].getMeeting(), jm_pairs[i].getJudge());
            addNode(jm_node);
        }

        Node sink(++next_id);
        addNode(sink);

        // Create edges from source to each room node
        for (int i = 1; i <= num_rooms; i++) {
            addEdge(0, i, ceil((double)(num_meetings) / (double)num_rooms));
        }

        // Create edges from each room to each meeting-judge pair
        for (int i = 1; i <= num_rooms; i++) {
            for (int j = 1; j <= num_meetings; j++) {
                addEdge(i, num_rooms + j, 1);
            }
        }

        // Create edges from each meeting-judge pair to the sink
        for (int i = 1; i <= num_meetings; i++) {
            addEdge(num_rooms + i, num_rooms + num_meetings + 1, 1);
        }
    }

    void initialize_v1_graph(const vector<Meeting>& meetings, const vector<Judge>& judges, const vector<Room>& rooms) {
        // Set the number of meetings, judges, and rooms from the passed vectors.
        if (meetings.size() > UINT32_MAX || judges.size() > UINT32_MAX || rooms.size() > UINT32_MAX) {
            throw invalid_argument("Too many meetings, judges, or rooms");
        }
        num_meetings = (int)meetings.size();
        num_judges   = (int)judges.size();
        num_rooms    = (int)rooms.size();
        num_jr_pairs = num_judges * num_rooms;

        int next_id = 0;
        Node source(++next_id);
        addNode(source);

        // Create a node for each judge
        for (int i = 0; i < num_judges; i++) {
            JudgeNode judge_node(++next_id, judges[i]);
            addNode(judge_node);
        }

        // Create a node for each meeting

        for (int i = 0; i < num_meetings; i++) {
            MeetingNode meeting_node(++next_id, 1, meetings[i]);
            addNode(meeting_node);
        }

        // Create a node for each room
        for (int i = 0; i < num_rooms; i++) {
            RoomNode room_node(++next_id, rooms[i]);
            addNode(room_node);
        }

        Node sink(++next_id);
        addNode(sink);

        /*//Create edges from source to each judge
        int judge_capacity = ceil(num_meetings / num_judges);
        for (int i = 1; i <= num_judges; i++) {
            addEdge(0, i, judge_capacity + 1);
        }*/

        // Create edges from source to each judge
        for (int i = 1; i <= num_judges; i++) {
            int compatible_meetings = 0;
            int skill_overlap       = 1; // Start with 1 to avoid division by zero

            for (int j = 0; j < num_meetings; j++) {
                if (judge_has_skill(judges[i - 1], meetings[j].meeting_sagstype)) {
                    compatible_meetings++;
                }
            }

            for (int j = 0; j < num_judges; j++) {
                if (i - 1 != j && // Don't compare judge with itself
                    (judge_has_skill(judges[i - 1], judges[j].judge_skills[0]) &&
                     judge_has_skill(judges[i - 1], judges[j].judge_skills[1]))) {
                    skill_overlap++;
                }
            }

            int judge_capacity = ceil((double)compatible_meetings / (double)skill_overlap);
            judge_capacity     = max(1, judge_capacity);

            addEdge(0, i, judge_capacity);
        }

        // Create edeges from each judge to each meeting
        for (int i = 1; i <= num_judges; i++) {
            auto& judge = judges[i - 1];
            for (int j = 1; j <= num_meetings; j++) {
                auto& meeting = meetings[j - 1];

                if (judge_has_skill(judge, meeting.meeting_sagstype)) {
                    addEdge(i, num_judges + j, 1);
                }
            }
        }

        // Create edges from each meeting to each room
        for (int i = 1; i <= num_meetings; i++) {
            for (int j = 1; j <= num_rooms; j++) {
                addEdge(num_judges + i, num_judges + num_meetings + j, 1);
            }
        }

        // Create edges from each room to the sink
        int room_capacity = ceil(num_meetings / num_rooms);
        for (int i = 1; i <= num_rooms; i++) {
            addEdge(num_judges + num_meetings + i, num_judges + num_meetings + num_rooms + 1, room_capacity + 1);
        }
    }

    void visualize() const {
        cout << "\nGraph Visualization:\n";
        cout << "==================\n\n";

        // Print nodes with additional details.
        cout << "Nodes:\n";
        cout << "------\n";
        for (size_t i = 0; i < nodes.size(); i++) {
            cout << "Node " << i << ": ";
            // Get the node id (which is set when the node is created)
            int nodeId = nodes[i]->getId();
            // Check for source node
            if (nodeId == 0) {
                cout << "Source Node";
            }
            // Check for meeting node
            else if (auto* meeting_node = dynamic_cast<MeetingNode*>(nodes[i].get())) {
                const Meeting& m = meeting_node->getMeeting();
                cout << "Meeting (ID: " << m.meeting_id
                     << ", Duration: " << m.meeting_duration
                     << ", Sagstype: ";
                switch (m.meeting_sagstype) {
                case Sagstype::Straffe:
                    cout << "Straffe";
                    break;
                case Sagstype::Civile:
                    cout << "Civile";
                    break;
                case Sagstype::Tvang:
                    cout << "Tvang";
                    break;
                }
                cout << ", Virtual: " << std::boolalpha << m.meeting_virtual << ")";
            }
            // Check for judge-room node
            else if (auto* jr_node = dynamic_cast<JudgeRoomNode*>(nodes[i].get())) {
                const Judge& j = jr_node->getJudge();
                const Room& r  = jr_node->getRoom();
                cout << "Judge-Room (Judge ID: " << j.judge_id
                     << ", Virtual: " << std::boolalpha << j.judge_virtual
                     << ", Skills: [";
                for (size_t k = 0; k < j.judge_skills.size(); k++) {
                    switch (j.judge_skills[k]) {
                    case Sagstype::Straffe:
                        cout << "Straffe";
                        break;
                    case Sagstype::Civile:
                        cout << "Civile";
                        break;
                    case Sagstype::Tvang:
                        cout << "Tvang";
                        break;
                    }
                    if (k != j.judge_skills.size() - 1)
                        cout << ", ";
                }
                cout << "], Room ID: " << r.room_id
                     << ", Virtual: " << std::boolalpha << r.room_virtual << ")";
            }
            // Check for meeting-judge-room node
            else if (auto* mjr_node = dynamic_cast<MeetingJudgeRoomNode*>(nodes[i].get())) {
                const Meeting& m = mjr_node->getMeeting();
                const Judge& j   = mjr_node->getJudge();
                const Room& r    = mjr_node->getRoom();
                cout << "Meeting-Judge-Room (Meeting ID: " << m.meeting_id
                     << ", Judge ID: " << j.judge_id
                     << ", Room ID: " << r.room_id << ")";
            }
            // Check for judge aggregate node
            else if (nodeId >= num_meetings + num_judges * num_rooms &&
                     nodeId < num_meetings + num_judges * num_rooms + num_judges) {
                int judge_id = nodeId - (num_meetings + num_judges * num_rooms) + 1;
                cout << "Judge Aggregate Node (Judge ID: " << judge_id << ")";
            } else if (nodeId >= num_meetings + num_judges * num_rooms + num_judges &&
                       nodeId < num_meetings + num_judges * num_rooms + num_judges + num_rooms) {
                int room_id = nodeId - (num_meetings + num_judges * num_rooms + num_judges) + 1;
                cout << "Room Aggregate Node (Room ID: " << room_id << ")";
            }
            // Check for sink node (assuming it was added last with id computed in initialize_v1_graph)
            else if (nodeId == 1 + num_meetings + num_judges * num_rooms + num_judges + num_rooms) {
                cout << "Sink Node";
            }
            // Fall back to generic node label if none of the above apply
            else {
                cout << "Generic Node";
            }
            cout << endl;
        }

        // [The rest of your visualization code for edges and the adjacency list remains unchanged]
        cout << "\nEdges:\n";
        cout << "------\n";
        for (const auto& edge : edges) {
            cout << edge.getFrom() << " -> " << edge.getTo()
                 << " (Capacity: " << edge.getCapacity()
                 << ", Flow: " << edge.getFlow() << ")" << endl;
        }

        cout << "\nAdjacency List:\n";
        cout << "--------------\n";
        for (size_t i = 0; i < adj_list.size(); i++) {
            cout << i << " (" << adj_list[i].size() << " outgoing edges) -> ";
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
