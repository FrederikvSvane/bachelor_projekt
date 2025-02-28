#pragma once

#include "../../domain/graph/graph.hpp"
#include <random>
#include <queue>

using namespace std;

namespace matching {

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


    // Add this to the matching namespace in matching.hpp

    bool bfs(DirectedGraph& graph, int source, int sink, vector<int>& parent) {
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

            vector<unordered_map<int, Edge*>> adj_list = graph.get_adj_list();
            // Get all adjacent vertices
            for (const auto& [v, edge] : adj_list[u]) {
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
                Edge* edge = graph.getEdge(u, v);
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
                Edge* edge = graph.getEdge(u, v);
                if (edge) {
                    edge->setFlow(edge->getFlow() + path_flow);
                }
            }

            // If we identified both a judge and a meeting, create a pair
            if (judge_node != -1 && meeting_node != -1) {
                auto* judge_node_ptr = graph.getNode<JudgeNode>(judge_node);
                auto* meeting_node_ptr = graph.getNode<MeetingNode>(meeting_node);

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
                Edge* edge = graph.getEdge(u, v);
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
                Edge* edge = graph.getEdge(u, v);
                if (edge) {
                    edge->setFlow(edge->getFlow() + path_flow);
                }
            }

            // If we identified both a room and a jm-pair, create an assignment
            if (room_node != -1 && jm_node != -1) {
                auto* room_node_ptr = graph.getNode<RoomNode>(room_node);
                auto* jm_node_ptr = graph.getNode<MeetingJudgeNode>(jm_node - graph.num_rooms);

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



    // BFS-based augmenting path finder for Ford-Fulkerson
    bool bfs_v1(DirectedGraph &graph, int source, int sink, vector<int> &parent) {
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

    vector<MeetingJudgeRoomNode> assign_meetings_to_judge_room_pairs(DirectedGraph &graph) {
        // Initialize random number generator
        vector<MeetingJudgeRoomNode> assigned_meetings;
        random_device rd;
        mt19937 gen(rd());

        // available JudgeRoomNodes indices
        vector<int> available_jr_nodes;

        // Helper to populate the available nodes list
        auto populate_available_nodes = [&]() {
            available_jr_nodes.clear();
            for (int i = 0; i < graph.num_jr_pairs; i++) {
                available_jr_nodes.push_back(graph.num_meetings + i);
            }
        };

        for (int i = 0; i < graph.num_meetings; i++) {
            if ((graph.num_meetings - i <= graph.num_meetings % graph.num_jr_pairs &&
                 graph.num_meetings % graph.num_jr_pairs != 0) || graph.num_meetings < graph.num_jr_pairs) {
                // random assignment and elimination of options
                if (available_jr_nodes.empty()) {
                    populate_available_nodes();
                }
                // generate random number between 0 and num_jr_pairs-1 (indexes of vector)
                uniform_int_distribution<> dist(0, available_jr_nodes.size() - 1);
                int random_idx = dist(gen);
                int chosen_jr_pair_id = available_jr_nodes[random_idx];

                // get the judge and room from the selected jr_pair
                auto *jr_node = graph.getNode<JudgeRoomNode>(chosen_jr_pair_id);
                auto *meeting_node = graph.getNode<MeetingNode>(i);

                // assign current meeting to the randomly chosen judgeroom pair
                MeetingJudgeRoomNode assignment(i, meeting_node->getMeeting(),
                                                jr_node->getJudge(), jr_node->getRoom());
                assigned_meetings.push_back(assignment);

                // eliminate all judgeroom pairs from the map/list of available judge room paris if they have the same judge or same room
                auto it = available_jr_nodes.begin();
                while (it != available_jr_nodes.end()) {
                    auto *node = graph.getNode<JudgeRoomNode>(*it);
                    if (node->getJudge().judge_id == jr_node->getJudge().judge_id ||
                        node->getRoom().room_id == jr_node->getRoom().room_id) {
                        it = available_jr_nodes.erase(it);
                    } else {
                        ++it;
                    }
                }
            } else {
                // regular straight assignment
                int jr_pair = i %
                              graph.num_jr_pairs; // we do this because it could happen that we have 9 meetings and 4 jr_pairs
                auto *jr_node = graph.getNode<JudgeRoomNode>(graph.num_meetings + jr_pair);
                auto *meeting_node = graph.getNode<MeetingNode>(i);
                MeetingJudgeRoomNode assignment(i, meeting_node->getMeeting(),
                                                jr_node->getJudge(), jr_node->getRoom());
                assigned_meetings.push_back(assignment);
            }
        }
        return assigned_meetings;
    }

} // namespace matching
