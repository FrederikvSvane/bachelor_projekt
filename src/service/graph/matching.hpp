#ifndef matching_hpp
#define matching_hpp

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

vector<MeetingJudgeRoomNode> assign_meetings_to_judge_room_pairs(DirectedGraph& graph) {
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
        if ((graph.num_meetings - i <= graph.num_meetings % graph.num_jr_pairs && graph.num_meetings % graph.num_jr_pairs != 0) || graph.num_meetings < graph.num_jr_pairs) {
            // random assignment and elimination of options
            if (available_jr_nodes.empty()) {
                populate_available_nodes();
            }
            // generate random number between 0 and num_jr_pairs-1 (indexes of vector)
            uniform_int_distribution<> dist(0, available_jr_nodes.size() - 1);
            int random_idx        = dist(gen);
            int chosen_jr_pair_id = available_jr_nodes[random_idx];

            // get the judge and room from the selected jr_pair
            auto* jr_node      = graph.getNode<JudgeRoomNode>(chosen_jr_pair_id);
            auto* meeting_node = graph.getNode<MeetingNode>(i);

            // assign current meeting to the randomly chosen judgeroom pair
            MeetingJudgeRoomNode assignment(i, meeting_node->getMeeting(),
                                            jr_node->getJudge(), jr_node->getRoom());
            assigned_meetings.push_back(assignment);

            // eliminate all judgeroom pairs from the map/list of available judge room paris if they have the same judge or same room
            auto it = available_jr_nodes.begin();
            while (it != available_jr_nodes.end()) {
                auto* node = graph.getNode<JudgeRoomNode>(*it);
                if (node->getJudge().judge_id == jr_node->getJudge().judge_id ||
                    node->getRoom().room_id == jr_node->getRoom().room_id) {
                    it = available_jr_nodes.erase(it);
                } else {
                    ++it;
                }
            }
        } else {
            // regular straight assignment
            int jr_pair        = i % graph.num_jr_pairs; // we do this because it could happen that we have 9 meetings and 4 jr_pairs
            auto* jr_node      = graph.getNode<JudgeRoomNode>(graph.num_meetings + jr_pair);
            auto* meeting_node = graph.getNode<MeetingNode>(i);
            MeetingJudgeRoomNode assignment(i, meeting_node->getMeeting(),
                                            jr_node->getJudge(), jr_node->getRoom());
            assigned_meetings.push_back(assignment);
        }
    }
    return assigned_meetings;
}

} // namespace matching

#endif