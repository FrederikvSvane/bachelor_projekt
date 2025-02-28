#pragma once

#include "domain/graph/graph.hpp"
#include <random>
#include <queue>

using namespace std;

namespace matching_v1 {

    struct AugmentingPath {
        int judge_node;
        int meeting_node;
        int room_node;
        int flow;
    };


    UndirectedGraph constructConflictGraph(vector<MeetingJudgeRoomNode> assigned_meetings) {
        UndirectedGraph conflict_graph(assigned_meetings.size());

        for (int i = 0; i < assigned_meetings.size(); i++) {
            conflict_graph.addNode(assigned_meetings[i]);
        }

        // iterate over all pairs of meetings
        for (int i = 0; i < conflict_graph.n_nodes; i++) {
            for (int j = 0; j < conflict_graph.n_nodes; j++) {
                if (i == j)
                    continue;
                // add an edge between the two meetings in the conflict graph if the two meetings have the same judge or room
                if (assigned_meetings[i].getJudge().judge_id == assigned_meetings[j].getJudge().judge_id ||
                    assigned_meetings[i].getRoom().room_id == assigned_meetings[j].getRoom().room_id) {
                    conflict_graph.addEdge(i, j);
                }
            }
        }

        return conflict_graph;
    }


    // BFS-based augmenting path finder for Ford-Fulkerson
    bool bfs(DirectedGraph &graph, int source, int sink, vector<int> &parent) {
        int n = graph.getNumNodes();
        vector<bool> visited(n, false);
        queue<int> q;

        // Start at source
        q.push(source);
        visited[source] = true;
        parent[source] = -1;

        // BFS loop
        while (!q.empty()) {
            int u = q.front();
            q.pop();

            vector<unordered_map<int, Edge *>> adj_list = graph.get_adj_list();
            // Check all neighbors of current node
            for (const auto &[v, edge] : adj_list[u]) {
                // Check if v is a meeting node and if its capacity is reached
                bool meetingNodeCapacityReached = false;
                if (v > graph.num_judges && v <= graph.num_judges + graph.num_meetings) {
                    auto* meetingNode = graph.getNode<MeetingNode>(v);
                    if (meetingNode && meetingNode->getFlow() >= meetingNode->getCapacity()) {
                        meetingNodeCapacityReached = true;
                    }
                }

                // If not visited, has remaining edge capacity, and meeting node capacity not reached
                if (!visited[v] && edge->getCapacity() > edge->getFlow() && !meetingNodeCapacityReached) {
                    q.push(v);
                    visited[v] = true;
                    parent[v] = u;

                    if (v == sink)
                        return true; // Found path to sink
                }
            }
        }

        // No path to sink found
        return false;
    }

    // Extract the judge, meeting, and room from an augmenting path
    AugmentingPath extractPathInfo(const vector<int> &parent, DirectedGraph &graph, int source, int sink, int path_flow) {
        AugmentingPath path = {-1, -1, -1, path_flow};

        // Reconstruct the path from sink to source
        for (int v = sink; v != source; v = parent[v]) {
            int u = parent[v];

            // Identify node types along the path

            // Check if u is a judge node (1 to num_judges)
            if (u >= 1 && u <= graph.num_judges) {
                path.judge_node = u;
            }

                // Check if u is a meeting node (num_judges+1 to num_judges+num_meetings)
            else if (u > graph.num_judges && u <= graph.num_judges + graph.num_meetings) {
                path.meeting_node = u;
            }

            // Check if v is a room node (num_judges+num_meetings+1 to num_judges+num_meetings+num_rooms)
            if (v > graph.num_judges + graph.num_meetings &&
                v <= graph.num_judges + graph.num_meetings + graph.num_rooms) {
                path.room_node = v;
            }
        }

        return path;
    }

    void printAugmentingPath(const AugmentingPath& path, DirectedGraph& graph, int pathNum) {
        cout << "Augmenting Path #" << pathNum << ":" << endl;
        cout << "  Flow Amount: " << path.flow << endl;

        if (path.judge_node != -1) {
            auto *judge_node = graph.getNode<JudgeNode>(path.judge_node);
            if (judge_node) {
                const Judge &judge = judge_node->getJudge();
                cout << "  Judge: ID=" << judge.judge_id << ", Skills=[";
                for (size_t i = 0; i < judge.judge_skills.size(); i++) {
                    switch (judge.judge_skills[i]) {
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
                    if (i < judge.judge_skills.size() - 1) cout << ", ";
                }
                cout << "]" << endl;
            }
        }

        if (path.meeting_node != -1) {
            auto *meeting_node = graph.getNode<MeetingNode>(path.meeting_node);
            if (meeting_node) {
                const Meeting &meeting = meeting_node->getMeeting();
                cout << "  Meeting: ID=" << meeting.meeting_id << ", Duration=" << meeting.meeting_duration;
                cout << ", Type=";
                switch (meeting.meeting_sagstype) {
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
                cout << endl;
            }
        }

        if (path.room_node != -1) {
            auto *room_node = graph.getNode<RoomNode>(path.room_node);
            if (room_node) {
                const Room &room = room_node->getRoom();
                cout << "  Room: ID=" << room.room_id << ", Virtual=" << (room.room_virtual ? "Yes" : "No") << endl;
            }
        }

        cout << "  Path: Source -> ";
        if (path.judge_node != -1) cout << "Judge(" << path.judge_node << ") -> ";
        if (path.meeting_node != -1) cout << "Meeting(" << path.meeting_node << ") -> ";
        if (path.room_node != -1) cout << "Room(" << path.room_node << ") -> ";
        cout << "Sink" << endl;
        cout << "----------------------------------------" << endl;

    }
    // Main Ford-Fulkerson implementation with path tracking
    vector<MeetingJudgeRoomNode> ford_fulkerson_v1(DirectedGraph &graph) {
        // Define source and sink
        int source = 0;
        int sink = graph.getNumNodes() - 1;
        int total_flow = 0;

        // Parent array for storing augmenting paths
        vector<int> parent(graph.getNumNodes(), -1);

        // Keep track of all augmenting paths
        vector<AugmentingPath> augmenting_paths;

        cout << "\n=== Ford-Fulkerson Augmenting Paths ===" << endl;
        cout << "========================================" << endl;
        int pathCounter = 1;

        // Run Ford-Fulkerson algorithm
        while (bfs(graph, source, sink, parent)) {
            // Find bottleneck capacity along the path
            int path_flow = numeric_limits<int>::max();
            for (int v = sink; v != source; v = parent[v]) {
                int u = parent[v];
                Edge* edge = graph.getEdge(u, v);
                if (edge) {
                    path_flow = min(path_flow, edge->getCapacity() - edge->getFlow());
                }
            }

            // Extract the judge, meeting, and room from this path
            AugmentingPath path_info = extractPathInfo(parent, graph, source, sink, path_flow);

            // Only record valid paths (should have all three nodes)
            if (path_info.judge_node != -1 && path_info.meeting_node != -1 && path_info.room_node != -1) {
                // Print path information
                printAugmentingPath(path_info, graph, pathCounter++);
                augmenting_paths.push_back(path_info);
            }

            // Update residual capacities
            for (int v = sink; v != source; v = parent[v]) {
                int u = parent[v];

                // Update meeting node flow if u is a meeting node
                if (u > graph.num_judges && u <= graph.num_judges + graph.num_meetings) {
                    auto* meetingNode = graph.getNode<MeetingNode>(u);
                    if (meetingNode) {
                        meetingNode->setFlow(meetingNode->getFlow() + path_flow);
                    }
                }

                Edge* edge = graph.getEdge(u, v);
                if (edge) {
                    edge->setFlow(edge->getFlow() + path_flow);
                }

                // Handle reverse edge (for residual graph)
                Edge* rev_edge = graph.getEdge(v, u);
                if (rev_edge) {
                    rev_edge->setFlow(rev_edge->getFlow() - path_flow);
                }
            }

            total_flow += path_flow;
        }

        // Check if all meetings were assigned
        if (total_flow < graph.num_meetings) {
            throw runtime_error("Not all meetings could be assigned: flow = "
                                + to_string(total_flow) + ", meetings = " + to_string(graph.num_meetings));
        }

        cout << "\n=== Summary of Assignments ===" << endl;
        cout << "Total Flow: " << total_flow << " (Should equal number of meetings: " << graph.num_meetings << ")" << endl;
        cout << "Total Paths Found: " << augmenting_paths.size() << endl;
        cout << "================================" << endl;

        // Convert augmenting paths to MeetingJudgeRoomNode objects
        vector<MeetingJudgeRoomNode> assigned_meetings;
        for (const auto& path : augmenting_paths) {
            auto* meeting_node = graph.getNode<MeetingNode>(path.meeting_node);
            auto* judge_node = graph.getNode<JudgeNode>(path.judge_node);
            auto* room_node = graph.getNode<RoomNode>(path.room_node);

            if (meeting_node && judge_node && room_node) {
                MeetingJudgeRoomNode assignment(
                        assigned_meetings.size(),  // Use index as ID
                        meeting_node->getMeeting(),
                        judge_node->getJudge(),
                        room_node->getRoom()
                );
                assigned_meetings.push_back(assignment);

                cout << "Assignment " << assigned_meetings.size() << ": Meeting "
                     << meeting_node->getMeeting().meeting_id << " -> Judge "
                     << judge_node->getJudge().judge_id << " -> Room "
                     << room_node->getRoom().room_id << endl;
            }
        }

        return assigned_meetings;
    }

} // namespace matching
