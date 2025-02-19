#ifndef schedule_hpp
#define schedule_hpp

#include <vector>
#include <sstream>

#include "appointment.hpp"
#include "graph.hpp"

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

    void generateScheduleFromColoredGraph(const UndirectedGraph& graph) {
        
        for(int i = 0; i < graph.n_nodes; i++){
            MeetingJudgeRoomNode* mjr_node = dynamic_cast<MeetingJudgeRoomNode*>(graph.nodes[i].get());
            int day = ceil(mjr_node->getColor() / timeslots_per_work_day);
            appointments.emplace_back(mjr_node->getMeeting(), mjr_node->getJudge(), mjr_node->getRoom(), day, mjr_node->getColor(), 5);
        }
        return;
    }

    string getTimeFromTimeslot(int timeslot) const {
        int day_timeslot = timeslot % timeslots_per_work_day;
        int minutes = day_timeslot * granularity; // fejl skal være timeslot_duration * g
        int hours = minutes / 60;
        minutes = minutes % 60;
        
        stringstream ss;
        ss << setfill('0') << setw(2) << hours << ":" << setfill('0') << setw(2) << minutes;
        return ss.str();
    }

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
    
        // Create a map of appointments by day
        unordered_map<int, vector<Appointment>> appointments_by_day;
        for (const auto& app : appointments) {
            appointments_by_day[app.day].push_back(app);
        }
    
        // Print daily schedules
        for (int day = 0; day < work_days; day++) {
            cout << "Day " << day + 1 << ":\n";
            cout << string(50, '-') << "\n";
            cout << setw(10) << "Time" << " | " 
                 << setw(10) << "Meeting" << " | " 
                 << setw(10) << "Judge" << " | " 
                 << setw(10) << "Room" << " | "
                 << setw(10) << "Duration" << "\n";
            cout << string(50, '-') << "\n";
    
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
                         << setw(10) << app.meeting.meeting_id << " | "
                         << setw(10) << app.judge.judge_id << " | "
                         << setw(10) << app.room.room_id << " | "
                         << setw(10) << app.timeslots_duration * granularity << " min\n";
                }
            } else {
                cout << "No appointments scheduled\n";
            }
            cout << string(50, '-') << "\n\n";
        }
    }

};

#endif