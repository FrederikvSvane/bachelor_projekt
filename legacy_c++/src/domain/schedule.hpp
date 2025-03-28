#pragma once

#include <algorithm>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

#include "../utils/parser.hpp"
#include "appointment.hpp"
#include "graph/graph.hpp"
#include "service/graph/coloring.hpp"
#include "service/graph/matching/matching_v1.hpp"
#include "service/graph/matching/matching_v2.hpp"

using namespace std;

struct Schedule {
    vector<Appointment> appointments;
    int timeslots_per_work_day;
    int work_days;
    int minutes_in_a_work_day;
    int granularity;

    Schedule(int wds, int mpwd, int g) : work_days(wds), minutes_in_a_work_day(mpwd), granularity(g) {
        timeslots_per_work_day = minutes_in_a_work_day / granularity - 1;
    }

    // Generate appointments using the node "color" as timeslot.
    void generateScheduleFromColoredGraph(const UndirectedGraph& graph) {
        for (int i = 0; i < graph.n_nodes; i++) {
            MeetingJudgeRoomNode* mjr_node = dynamic_cast<MeetingJudgeRoomNode*>(graph.nodes[i].get());
            // Determine the day based on timeslot (color) and timeslots per day
            int day = (mjr_node->getColor() / timeslots_per_work_day);
            appointments.emplace_back(mjr_node->getMeeting(), mjr_node->getJudge(), mjr_node->getRoom(), day, mjr_node->getColor(), mjr_node->getMeeting().meeting_duration);
        }
    }

    // Converts a timeslot index into a time string based on granularity.
    string getTimeFromTimeslot(int timeslot) const {
        int day_timeslot = timeslot % timeslots_per_work_day;
        int minutes      = day_timeslot * granularity;
        int hours        = minutes / 60;
        minutes          = minutes % 60;

        stringstream ss;
        ss << setfill('0') << setw(2) << hours << ":" << setfill('0') << setw(2) << minutes;
        return ss.str();
    }

    // Visualizes the schedule in a table format.
    void visualize() const {
        cout << "\nSchedule Visualization\n";
        cout << "=====================\n\n";

        // Print schedule statistics
        cout << "Schedule Statistics:\n";
        cout << "-------------------\n";
        cout << "Work days: " << work_days << "\n";
        cout << "Minutes per work day: " << minutes_in_a_work_day << "\n";
        cout << "Time slot granularity: " << granularity << " minutes\n";
        cout << "Time slots per day: " << timeslots_per_work_day << "\n";
        cout << "Total appointments: " << appointments.size() << "\n\n";

        // Map appointments by day
        unordered_map<int, vector<Appointment>> appointments_by_day;
        for (const auto& app : appointments) {
            appointments_by_day[app.day].push_back(app);
        }

        // Print daily schedule with an added Timeslot (raw color) column.
        for (int day = 0; day < work_days; day++) {
            cout << "Day " << day + 1 << ":\n";
            cout << string(70, '-') << "\n";
            cout << setw(10) << "Time" << " | "
                 << setw(10) << "Timeslot" << " | "
                 << setw(10) << "Meeting" << " | "
                 << setw(10) << "Judge" << " | "
                 << setw(10) << "Room" << " | "
                 << setw(10) << "Duration" << "\n";
            cout << string(70, '-') << "\n";

            if (appointments_by_day.count(day) > 0) {
                // Sort appointments by timeslot
                auto& day_appointments = appointments_by_day[day];
                sort(day_appointments.begin(), day_appointments.end(),
                     [](const Appointment& a, const Appointment& b) {
                         return a.timeslot_start < b.timeslot_start;
                     });

                // Print each appointment
                for (const auto& app : day_appointments) {
                    cout << setw(10) << getTimeFromTimeslot(app.timeslot_start) << " | "
                         << setw(10) << app.timeslot_start << " | "
                         << setw(10) << app.meeting.meeting_id << " | "
                         << setw(10) << app.judge.judge_id << " | "
                         << setw(10) << app.room.room_id << " | "
                         << setw(10) << app.timeslots_duration << " min\n";
                }
            } else {
                cout << "No appointments scheduled\n";
            }
            cout << string(70, '-') << "\n\n";
        }
    }
};


Schedule generateScheduleUsingTwoStepApproach(const parser::ParsedData& parsed_data) {
    // Extract input parameters
    int work_days = parsed_data.work_days;
    int minutes_per_work_day = parsed_data.min_per_work_day;
    int granularity = parsed_data.granularity;

    std::vector<Meeting> meetings = parsed_data.meetings;
    std::vector<Judge> judges = parsed_data.judges;
    std::vector<Room> rooms = parsed_data.rooms;

    int n_meetings = static_cast<int>(meetings.size());
    int n_judges = static_cast<int>(judges.size());
    int n_rooms = static_cast<int>(rooms.size());

    // Step 1: Assign judges to meetings based on skills
    cout << "\n=== Step 1: Assigning Judges to Meetings ===" << endl;
    DirectedGraph judge_case_graph(n_meetings + n_judges + 2);  // +2 for source and sink
    judge_case_graph.initialize_judge_case_graph(meetings, judges);

    judge_case_graph.visualize();

    vector<MeetingJudgeNode> meeting_judge_pairs = matching_v2::assign_judges_to_meetings(judge_case_graph);

    // Step 2: Assign rooms to meeting-judge pairs
    cout << "\n=== Step 2: Assigning Rooms to Judge-Meeting Pairs ===" << endl;
    DirectedGraph jm_room_graph(meeting_judge_pairs.size() + n_rooms + 2);  // +2 for source and sink
    jm_room_graph.initialize_jm_graph(meeting_judge_pairs, rooms);

    jm_room_graph.visualize();

    vector<MeetingJudgeRoomNode> assigned_meetings = matching_v2::assign_rooms_to_jm_pairs(jm_room_graph);

    // Construct conflict graph
    cout << "\n=== Step 3: Creating Conflict Graph ===" << endl;
    UndirectedGraph conflict_graph = matching_v2::constructConflictGraph(assigned_meetings);

    // Perform graph coloring
    cout << "\n=== Step 4: Coloring Conflict Graph ===" << endl;
    coloring::colorConflictGraph(conflict_graph);
    conflict_graph.visualize();

    // Generate schedule
    cout << "\n=== Step 5: Generating Final Schedule ===" << endl;
    Schedule schedule(work_days, minutes_per_work_day, granularity);
    schedule.generateScheduleFromColoredGraph(conflict_graph);

    return schedule;
}

Schedule generateScheduleUsingGraphs(const parser::ParsedData& parsed_data) {
    // Extract input parameters
    int work_days            = parsed_data.work_days;
    int minutes_per_work_day = parsed_data.min_per_work_day;
    int granularity          = parsed_data.granularity;

    std::vector<Meeting> meetings = parsed_data.meetings;
    std::vector<Judge> judges     = parsed_data.judges;
    std::vector<Room> rooms       = parsed_data.rooms;

    int n_meetings = static_cast<int>(meetings.size());
    int n_judges   = static_cast<int>(judges.size());
    int n_rooms    = static_cast<int>(rooms.size());

    // Initialize the graph
    DirectedGraph graph(n_meetings + n_judges + n_rooms + 2);
    graph.initialize_v1_graph(meetings, judges, rooms);

    graph.visualize();

    // Assign meetings to judge-room pairs
    std::vector<MeetingJudgeRoomNode> assigned_meetings = matching_v1::ford_fulkerson_v1(graph);

    // Construct solution graph
    DirectedGraph sol_graph(static_cast<int>(assigned_meetings.size()));
    for (const auto& appointment : assigned_meetings) {
        sol_graph.addNode(appointment);
    }

    // Construct conflict graph
    UndirectedGraph conflict_graph = matching_v1::constructConflictGraph(assigned_meetings);

    // Perform graph coloring
    coloring::colorConflictGraph(conflict_graph);

    // Generate schedule
    Schedule schedule(work_days, minutes_per_work_day, granularity);
    schedule.generateScheduleFromColoredGraph(conflict_graph);

    return schedule;
}