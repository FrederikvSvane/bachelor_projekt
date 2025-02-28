#pragma once

#include "domain/graph/graph.hpp"
#include <random>
#include <queue>

namespace matching_v2 {
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

// Add this to the matching namespace in matching.hpp
    bool bfs(DirectedGraph &graph, int source, int sink, vector<int> &parent) {
        // Initialize all vertices as not visited
        vector<bool> visited(graph.getNumNodes(), false);

        // Create a queue, enqueue source vertex
        queue<int> q;
        q.push(source);
        visited[source] = true;
        parent[source] = -1;

        // Standard BFS Loop
        while (!q.empty()) {
            int u = q.front();
            q.pop();

            vector<unordered_map<int, Edge *>> adj_list = graph.get_adj_list();
            // Get all adjacent vertices
            for (const auto &[v, edge]: adj_list[u]) {
                // If not visited and has remaining capacity
                if (!visited[v] && edge->getCapacity() > edge->getFlow()) {
                    // Add to queue and mark as visited
                    q.push(v);
                    parent[v] = u;
                    visited[v] = true;
                }
            }
        }

        // If we reached sink in BFS starting from source, return true
        return visited[sink];
    }

// Function to extract judge-meeting pairs from the first flow solution
    vector<MeetingJudgeNode> assign_judges_to_meetings(DirectedGraph &graph) {
        int source = 0;
        int sink = graph.getNumNodes() - 1;
        int total_flow = 0;

        vector<int> parent(graph.getNumNodes(), -1);
        vector<MeetingJudgeNode> assigned_pairs;

        cout << "\n=== Assigning Judges to Meetings ===" << endl;

        // Run Ford-Fulkerson
        while (bfs(graph, source, sink, parent)) {
            // Find bottleneck capacity
            int path_flow = numeric_limits<int>::max();
            for (int v = sink; v != source; v = parent[v]) {
                int u = parent[v];
                Edge *edge = graph.getEdge(u, v);
                if (edge) {
                    path_flow = min(path_flow, edge->getCapacity() - edge->getFlow());
                }
            }

            // Extract judge and meeting nodes from this path
            int judge_node = -1;
            int meeting_node = -1;

            for (int v = sink; v != source; v = parent[v]) {
                int u = parent[v];

                // Check if u is a judge node (1 to num_judges)
                if (u >= 1 && u <= graph.num_judges) {
                    judge_node = u;
                }

                // Check if v is a meeting node (num_judges+1 to num_judges+num_meetings)
                if (v > graph.num_judges && v <= graph.num_judges + graph.num_meetings) {
                    meeting_node = v;
                }

                // Update flow values
                Edge *edge = graph.getEdge(u, v);
                if (edge) {
                    edge->setFlow(edge->getFlow() + path_flow);
                }
            }

            // If we identified both a judge and a meeting, create a pair
            if (judge_node != -1 && meeting_node != -1) {
                auto *judge_node_ptr = graph.getNode<JudgeNode>(judge_node);
                auto *meeting_node_ptr = graph.getNode<MeetingNode>(meeting_node);

                if (judge_node_ptr && meeting_node_ptr) {
                    MeetingJudgeNode pair(
                            assigned_pairs.size(),  // Use index as ID
                            meeting_node_ptr->getMeeting(),
                            judge_node_ptr->getJudge()
                    );
                    assigned_pairs.push_back(pair);

                    cout << "Assignment " << assigned_pairs.size() << ": Meeting "
                         << meeting_node_ptr->getMeeting().meeting_id << " -> Judge "
                         << judge_node_ptr->getJudge().judge_id << endl;
                }
            }

            total_flow += path_flow;
        }

        // Check if all meetings were assigned
        if (total_flow < graph.num_meetings) {
            throw runtime_error("Not all meetings could be assigned judges: flow = "
                                + to_string(total_flow) + ", meetings = " + to_string(graph.num_meetings));
        }

        cout << "Total Meetings Assigned: " << assigned_pairs.size() << endl;
        cout << "================================" << endl;

        return assigned_pairs;
    }

// Function to assign rooms to judge-meeting pairs
    vector<MeetingJudgeRoomNode> assign_rooms_to_jm_pairs(DirectedGraph &graph) {
        int source = 0;
        int sink = graph.getNumNodes() - 1;
        int total_flow = 0;

        vector<int> parent(graph.getNumNodes(), -1);
        vector<MeetingJudgeRoomNode> assigned_meetings;

        cout << "\n=== Assigning Rooms to Judge-Meeting Pairs ===" << endl;

        // Run Ford-Fulkerson
        while (bfs(graph, source, sink, parent)) {
            // Find bottleneck capacity
            int path_flow = numeric_limits<int>::max();
            for (int v = sink; v != source; v = parent[v]) {
                int u = parent[v];
                Edge *edge = graph.getEdge(u, v);
                if (edge) {
                    path_flow = min(path_flow, edge->getCapacity() - edge->getFlow());
                }
            }

            // Extract room and jm-pair nodes from this path
            int room_node = -1;
            int jm_node = -1;

            for (int v = sink; v != source; v = parent[v]) {
                int u = parent[v];

                // Check if u is a room node (1 to num_rooms)
                if (u >= 1 && u <= graph.num_rooms) {
                    room_node = u;
                }

                // Check if v is a jm-pair node (num_rooms+1 to num_rooms+jm_pairs.size())
                if (v > graph.num_rooms && v <= graph.num_rooms + graph.num_meetings) {
                    jm_node = v;
                }

                // Update flow values
                Edge *edge = graph.getEdge(u, v);
                if (edge) {
                    edge->setFlow(edge->getFlow() + path_flow);
                }
            }

            // If we identified both a room and a jm-pair, create an assignment
            if (room_node != -1 && jm_node != -1) {
                auto *room_node_ptr = graph.getNode<RoomNode>(room_node);
                auto *jm_node_ptr = graph.getNode<MeetingJudgeNode>(jm_node - graph.num_rooms);

                if (room_node_ptr && jm_node_ptr) {
                    MeetingJudgeRoomNode assignment(
                            assigned_meetings.size(),  // Use index as ID
                            jm_node_ptr->getMeeting(),
                            jm_node_ptr->getJudge(),
                            room_node_ptr->getRoom()
                    );
                    assigned_meetings.push_back(assignment);

                    cout << "Assignment " << assigned_meetings.size() << ": Meeting "
                         << jm_node_ptr->getMeeting().meeting_id << " -> Judge "
                         << jm_node_ptr->getJudge().judge_id << " -> Room "
                         << room_node_ptr->getRoom().room_id << endl;
                }
            }

            total_flow += path_flow;
        }

        // Check if all jm-pairs were assigned
        if (total_flow < graph.num_meetings) {
            throw runtime_error("Not all judge-meeting pairs could be assigned rooms: flow = "
                                + to_string(total_flow) + ", pairs = " + to_string(graph.num_meetings));
        }

        cout << "Total Assignments: " << assigned_meetings.size() << endl;
        cout << "================================" << endl;

        return assigned_meetings;
    }
}