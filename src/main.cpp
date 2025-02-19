#include <iostream>
#include <cmath>

#include "graph.hpp"

int main(int argc, char const *argv[])
{
    Meeting m1(1);
    Meeting m2(2);
    Meeting m3(3);
    Meeting m4(4);
    Meeting m5(5);
    Meeting m6(6);
    Meeting m7(7);
    Meeting m8(8);
    Meeting m9(9);
    Judge j1(1);
    Judge j2(2);
    Judge j3(3);
    Room r1(1);
    Room r2(2);
    Room r3(3);

    DirectedGraph graph(20);

    Node source(0);
    Node sink(1);
    
    MeetingNode m_node1(2, m1);
    MeetingNode m_node2(3, m2);
    MeetingNode m_node3(4, m3);
    MeetingNode m_node4(5, m4);
    MeetingNode m_node5(6, m5);
    MeetingNode m_node6(7, m6);
    MeetingNode m_node7(8, m7);
    MeetingNode m_node8(9, m8);
    MeetingNode m_node9(10, m9);

    JudgeRoomNode judge_room_node1(11, j1, r1);
    JudgeRoomNode judge_room_node2(12, j1, r2);
    JudgeRoomNode judge_room_node3(13, j1, r3);
    JudgeRoomNode judge_room_node4(14, j3, r1);
    JudgeRoomNode judge_room_node5(15, j3, r2);
    JudgeRoomNode judge_room_node6(16, j3, r3);
    JudgeRoomNode judge_room_node7(17, j2, r1);
    JudgeRoomNode judge_room_node8(18, j2, r2);
    JudgeRoomNode judge_room_node9(19, j2, r3);

    graph.addNode(source);
    graph.addNode(sink);

    graph.addNode(m_node1);
    graph.addNode(m_node2);
    graph.addNode(m_node3);
    graph.addNode(m_node4);
    graph.addNode(m_node5);
    graph.addNode(m_node6);
    graph.addNode(m_node7);
    graph.addNode(m_node8);
    graph.addNode(m_node9);

    graph.addNode(judge_room_node1);
    graph.addNode(judge_room_node2);
    graph.addNode(judge_room_node3);
    graph.addNode(judge_room_node4);
    graph.addNode(judge_room_node5);
    graph.addNode(judge_room_node6);
    graph.addNode(judge_room_node7);
    graph.addNode(judge_room_node8);
    graph.addNode(judge_room_node9);


    // fra source til alle meeting nodes
    for(int i = 2; i <= 10; i++) {
        graph.addEdge(0, i, 1);
    }

    // fra hver meeting node til alle judge_room nodes
    for (int i = 2; i <= 10; i++) {
        for (int j = 11; j <= 19; j++) {
            graph.addEdge(i, j, 1);
        }
    }

    for(int i = 11; i <= 19; i++) {
        graph.addEdge(i, 1, ceil(9/9)); // capacity = ceil(meeting nodes / judge_room nodes)
    }



    graph.visualize();

    return 0;
}
