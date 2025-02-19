#ifndef coloring_hpp
#define coloring_hpp

#include "graph.hpp"
#include <set>

namespace coloring {

// Helper function to get saturation degree of a vertex
int getSaturationDegree(const UndirectedGraph& graph, int vertex) {
    set<int> neighbor_colors;
    for (int neighbor : graph.getNeighbors(vertex)) {
        int color = graph.getNode<Node>(neighbor)->getColor();
        if (color != -1) { // If neighbor is colored
            neighbor_colors.insert(color);
        }
    }
    return neighbor_colors.size();
}

int getNextNode(UndirectedGraph& graph) {
    int max_sat_degree = -1;
    int max_degree     = -1;
    int selected_node  = -1;

    for (int i = 0; i < graph.n_nodes; i++) {
        if (graph.getNode<Node>(i)->getColor() != -1)
            continue; // Skip colored vertices

        int sat_degree = getSaturationDegree(graph, i);
        int degree     = graph.getDegree(i);

        // Select node with highest saturation degree
        if (sat_degree > max_sat_degree) {
            max_sat_degree = sat_degree;
            max_degree     = degree;
            selected_node  = i;
        }
        // If tie in saturation degree, select node with highest degree
        else if (sat_degree == max_sat_degree) {
            if (degree > max_degree) {
                max_degree    = degree;
                selected_node = i;
            }
            // If tie in degree, select node with lowest id
            else if (degree == max_degree && (selected_node == -1 || i < selected_node)) {
                selected_node = i;
            }
        }
    }
    return selected_node;
}

int getLowestAvailableColor(const UndirectedGraph& graph, int vertex) {
    vector<bool> color_used(graph.n_nodes, false); // <false, false, ...>

    // mark all used color idecies
    for (int neighbor : graph.getNeighbors(vertex)) {
        int color = graph.getNode<Node>(neighbor)->getColor();
        if (color != -1) {
            color_used[color] = true;
        }
    }

    // Find lowest unused color
    for (int color = 0; color < graph.n_nodes; color++) {
        if (!color_used[color]) {
            return color;
        }
    }
    return -1; // Should never happen 
}

void colorConflictGraph(UndirectedGraph& graph) {
    // init all nodes to have no color
    for (int i = 0; i < graph.n_nodes; i++) {
        graph.getNode<Node>(i)->setColor(-1);
    }

    for (int i = 0; i < graph.n_nodes; i++) {
        // select node with highest sat deg
        // if tie, select node with highest deg
        // if tie, select node with lowest id

        int node = getNextNode(graph);
        if (node == -1)
            break; // All vertices are colored

        // try to set color of node to 1. Check if neighbor has this color. If yes, try next color. Check again. repeat untill lowest valid color is found
        int color = getLowestAvailableColor(graph, node);
        graph.getNode<Node>(node)->setColor(color);
    }
}

} // namespace coloring

#endif