#ifndef PARSER_HPP
#define PARSER_HPP

#include "json.hpp"          // The nlohmann::json header
#include <fstream>
#include <vector>
#include <stdexcept>
#include <iostream>

#include "../domain/meeting.hpp"
#include "../domain/judge.hpp"
#include "../domain/room.hpp"

using json = nlohmann::json;
using namespace::std;

namespace parser {

    struct ParsedData {
        vector<Meeting> meetings;
        vector<Judge> judges;
        vector<Room> rooms;
        int work_days = 0;
        int min_per_work_day = 0;
        int granularity = 0;
    };

    ParsedData parseJsonFile(json data) {

        // Prepare our result struct
        ParsedData result;

        // Parse "meetings"
        if (data.contains("meetings") && data["meetings"].is_array()) {
            for (const auto &meeting_json: data["meetings"]) {
                int id = meeting_json["id"].get<int>();
                int duration = meeting_json["duration"].get<int>();
                result.meetings.emplace_back(id, duration);
            }
        } else {
            std::cerr << "JSON does not contain a valid 'meetings' array.\n";
        }

        // Parse "CourtRooms"
        if (data.contains("CourtRooms") && data["CourtRooms"].is_array()) {
            for (const auto &court_room_json: data["CourtRooms"]) {
                int id = court_room_json["id"].get<int>();
                result.rooms.emplace_back(id);
            }
        } else {
            std::cerr << "JSON does not contain a valid 'CourtRooms' array.\n";
        }

        // Parse "Judges"
        if (data.contains("Judges") && data["Judges"].is_array()) {
            for (const auto &judge_json: data["Judges"]) {
                int id = judge_json["id"].get<int>();
                result.judges.emplace_back(id);
            }
        } else {
            std::cerr << "JSON does not contain a valid 'Judges' array.\n";
        }

        // Parse "work_days"
        if (data.contains("work_days") && data["work_days"].is_number()) {
            result.work_days = data["work_days"].get<int>();
        } else {
            std::cerr << "JSON does not contain a valid 'work_days' number.\n";
        }

        // Parse "min_per_work_day"
        if (data.contains("min_per_work_day") && data["min_per_work_day"].is_number()) {
            result.min_per_work_day = data["min_per_work_day"].get<int>();
        } else {
            std::cerr << "JSON does not contain a valid 'min_per_work_day' number.\n";
        }

        // Parse "granularity"
        if (data.contains("granularity") && data["granularity"].is_number()) {
            result.granularity = data["granularity"].get<int>();
        } else {
            std::cerr << "JSON does not contain a valid 'granularity' number.\n";
        }

        return result;
    }

}

#endif
