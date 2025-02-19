#include "graph.hpp"

int main(int argc, char const* argv[]) {
    const int n_meetings = 9;
    const int n_judges   = 3;
    const int n_rooms    = 3;
    DirectedGraph graph(1 + n_meetings + n_judges * n_rooms + 1);

    graph.initialize_flow_graph(n_meetings, n_judges, n_rooms);
    graph.visualize();

    return 0;
}
