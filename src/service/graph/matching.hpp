#pragma once

#include "../../domain/graph/graph.hpp"
#include <random>

using namespace std;

namespace matching {

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


    bool dfs(DirectedGraph &graph, int current, int sink, vector<bool> &visited, vector<int> &parent,
             const vector<unordered_map<int, Edge *>> &adj_list) {
        //Sets the current node to visited
        visited[current] = true;
        if (current == sink) return true;

        // Iterate over all outgoing edges from the current node.
        for (auto &edgePair: adj_list[current]) {
            // Get the next node and the edge object.
            int next = edgePair.first;
            Edge *edge = edgePair.second;
            // If the next node is not visited and the residual capacity is positive, recursively call DFS.
            int residual_capacity = edge->getCapacity() - edge->getFlow(); //How much flow can still be sent through
            if (!visited[next] && residual_capacity > 0) {
                parent[next] = current;
                if (dfs(graph, next, sink, visited, parent, adj_list))
                    return true; //Returns true if augmenting path is found
            }
        }
        return false;
    }

    //Using ford fulkerson approach with dfs to find augmenting paths and create the mjr nodes
    vector<MeetingJudgeRoomNode> assign_meetings_to_judge_rooms_pairs_flow(DirectedGraph &graph) {
        vector<MeetingJudgeRoomNode> assigned_meetings;

        // Define the source and sink node IDs based on your graph construction.
        int source = 0;
        int sink = graph.getNumNodes() - 1;
        int total_flow = 0;

        // Parent vector to store the augmenting path.
        vector<int> parent(graph.getNumNodes(), -1);

        // Run Ford-Fulkerson: while an augmenting path exists, send flow.
        while (true) {
            vector<bool> visited(graph.getNumNodes(), false);
            fill(parent.begin(), parent.end(), -1);

            // Try to find an augmenting path using DFS.
            if (!dfs(graph, source, sink, visited, parent, graph.get_adj_list()))
                break;  // No augmenting path found: maximum flow reached.

            // Determine the bottleneck capacity along the found path. By looping over all nodes in the path and checking their edges
            int path_flow = numeric_limits<int>::max(); //Sets path flow to max int value
            for (int v = sink; v != source; v = parent[v]) {
                int u = parent[v];
                Edge *edge = graph.getEdge(u, v);
                if (edge) {
                    path_flow = min(path_flow, edge->getCapacity() -
                                               edge->getFlow()); //Finds the minimum flow that can be sent through the path
                }
            }

            // Augment the flow along the path, set the flow all the edges in the path
            for (int v = sink; v != source; v = parent[v]) {
                int u = parent[v];
                Edge *edge = graph.getEdge(u, v);
                if (edge) {
                    edge->setFlow(edge->getFlow() + path_flow);
                }
            }
            total_flow += path_flow;
        }

        if (total_flow != graph.num_meetings) {
            throw runtime_error("Not all meetings were assigned");
        }


        vector<unordered_map<int, Edge *>> adj_list = graph.get_adj_list();
        // After maximum flow is reached, extract the assignments.
        // Loop over all meeting nodes and check their outgoing edges.
        for (int meetingId = 1; meetingId <= graph.num_meetings; ++meetingId) {
            for (auto &edgePair: adj_list[meetingId]) {
                int jr_node_id = edgePair.first;
                Edge *edge = edgePair.second;
                //When we find an edge with flow, we know that the meeting is assigned to the corresponding judge-room pair.
                //Effectively following the residual graph (even though we are not explicitly constructing it)
                if (edge->getFlow() > 0) {
                    auto *meetingNode = graph.getNode<MeetingNode>(meetingId);
                    auto *jrNode = graph.getNode<JudgeRoomNode>(jr_node_id);
                    if (meetingNode && jrNode) {
                        MeetingJudgeRoomNode assignment(meetingId, meetingNode->getMeeting(), jrNode->getJudge(),
                                                        jrNode->getRoom());
                        assigned_meetings.push_back(assignment);
                    }
                }
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
