#ifndef graph_hpp
#define graph_hpp

#include <iostream>
#include <stdexcept>
#include <tuple>
#include <variant>
#include <vector>
#include <memory>

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
        : from_id(from), to_id(to), capacity(cap) {}

    int getFrom() const { return from_id; }
    int getTo() const { return to_id; }
    int getCapacity() const { return capacity; }
    int getFlow() const { return flow; }
    void setFlow(int f) { flow = f; }
};

// Til max-flow
class Graph {
  private:
    vector<unique_ptr<Node>> nodes;
    vector<Edge> edges;
    vector<vector<int>> adj_list;

  public:
    void addNode(unique_ptr<Node> node) {
        adj_list.push_back({});
        nodes.push_back(std::move(node));
    }

    template <typename T>
    T* getNode(int id) {
        return dynamic_cast<T*>(nodes[id].get());
    }
};

// Til k-coloring
struct UndirectedGraph {
    int n_nodes;
    vector<Edge> edges;
    vector<vector<int>> adj_matrix;
};

#endif