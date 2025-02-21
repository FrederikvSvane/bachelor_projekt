#include "service/graph/coloring.hpp"
#include "domain/graph/graph.hpp"
#include "utils/json.hpp"
#include "service/graph/matching.hpp"
#include "domain/schedule.hpp"

using json = nlohmann::json;

int main(int argc, char const* argv[]) {
    const int n_meetings = 95;
    const int n_judges   = 17;
    const int n_rooms    = 4;
    // const int n_meetings = 9;
    // const int n_judges   = 3;
    // const int n_rooms    = 3;

    json example = {
        {"hard", true},
        {"soft", false},
    };

    DirectedGraph graph(n_meetings + n_judges * n_rooms);

    graph.initialize_bipartite_graph(n_meetings, n_judges, n_rooms);
    graph.visualize();

    vector<MeetingJudgeRoomNode> assigned_meetings = matching::assign_meetings_to_judge_room_pairs(graph);

    DirectedGraph sol_graph((int)assigned_meetings.size());
    for (const auto& appointment : assigned_meetings) {
        sol_graph.addNode(appointment);
    }
    sol_graph.visualize();

    UndirectedGraph conflict_graph = matching::constructConflictGraph(assigned_meetings);
    conflict_graph.visualize();

    coloring::colorConflictGraph(conflict_graph);
    conflict_graph.visualize();
    
    Schedule schedule(5, 300, 30);
    schedule.generateScheduleFromColoredGraph(conflict_graph);
    schedule.visualize();

    return 0;
}
