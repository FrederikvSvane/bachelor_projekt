#include "domain/graph/graph.hpp"
#include "domain/schedule.hpp"
#include "service/graph/coloring.hpp"
#include "service/graph/matching.hpp"
#include "utils/argparse.hpp"
#include "utils/json.hpp"
#include "utils/parser.hpp"
#include "utils/test_data_generator.hpp"
#include <filesystem>
#include <fstream>

using json = nlohmann::json;
using namespace ::parser;
using namespace ::std;
namespace fs = filesystem;

int main(int argc, char const* argv[]) {
    argparse::ArgumentParser program("CourtCaseScheduler");

    program.add_argument("-i", "--input")
        .help("Path to the input JSON file")
        .default_value(string(""));

    program.add_argument("-o", "--output")
        .help("Path to the output JSON file")
        .default_value(string("output.json"));

    program.add_argument("--test")
        .help("Use the test input file")
        .default_value(false)
        .implicit_value(true);

    try {
        program.parse_args(argc, argv);
    } catch (const exception& e) {
        cerr << "Argument parsing error: " << e.what() << endl;
        return 1;
    }

    ParsedData parsed_data;
    bool useTestFile = program.get<bool>("--test");
    auto fileToRead  = program.get<string>("--input");
    auto fileToWrite = program.get<string>("--output");
    json output_json;

    json data;
    if (useTestFile) {
        data = test_data_generator::generate_request(
            50,   // 5 meetings
            2,    // 2 judges
            2,    // 2 rooms
            2,    // 2 days
            30,   // 30 min granularity
            480,  // 480 min per day
            true // fixed request
        );
    } else {
        if (fileToRead.empty()) {
            cerr << "No input file specified. Use -i <file_path>.\n";
            return 1;
        }
        ifstream f(fileToRead);
        if (!f.is_open()) {
            cerr << "Error opening file: " << fileToRead << "\n";
            return 1;
        }
        data = json::parse(f);
    }

    try {
        parsed_data = parseJsonFile(data);
    } catch (const exception& e) {
        cerr << e.what() << endl;
        return 1;
    }

    vector<Meeting> meetings = parsed_data.meetings;
    vector<Judge> judges     = parsed_data.judges;
    vector<Room> rooms       = parsed_data.rooms;

    int work_days            = parsed_data.work_days;
    int minutes_per_work_day = parsed_data.min_per_work_day;
    int granularity          = parsed_data.granularity;
    int n_meetings           = static_cast<int>(meetings.size());
    int n_judges             = static_cast<int>(judges.size());
    int n_rooms              = static_cast<int>(rooms.size());


    DirectedGraph graph(n_meetings + n_judges * n_rooms);
    graph.initialize_bipartite_graph(meetings, judges, rooms);
    vector<MeetingJudgeRoomNode> assigned_meetings = matching::assign_meetings_to_judge_room_pairs(graph);

    UndirectedGraph conflict_graph = matching::constructConflictGraph(assigned_meetings);
    coloring::colorConflictGraph(conflict_graph);

    Schedule schedule(work_days, minutes_per_work_day, granularity);
    schedule.generateScheduleFromColoredGraph(conflict_graph);
    schedule.visualize();

    // Always write the output file to the root folder (current working directory)
    fs::path p(fileToWrite);
    string outputFilename = p.filename().string();

    ofstream out_file(outputFilename);
    if (!out_file.is_open()) {
        cerr << "Error opening output file: " << outputFilename << "\n";
        return 1;
    }
    return 0;
}
