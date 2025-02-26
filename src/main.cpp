#include "domain/graph/graph.hpp"
#include "domain/schedule.hpp"
#include "service/graph/coloring.hpp"
#include "utils/argparse.hpp"
#include "utils/json.hpp"
#include "utils/main_inlines.hpp"
#include "utils/parser.hpp"
#include <fstream>
#include <iostream>

using json = nlohmann::json;
using namespace std;
namespace fs = filesystem;

int main(int argc, char const* argv[]) {
    argparse::ArgumentParser program("CourtCaseScheduler");
    parseArguments(argc, argv, program);

    // reads input file, modifies parsed_data in memory and returns 0 if it fails. hacky.
    parser::ParsedData parsed_data;
    if (!handleInput(program, parsed_data, 100, false)) {
        return 1;
    }

    Schedule schedule = generateScheduleUsingGraphs(parsed_data);
    schedule.visualize();

    auto fileToWrite = program.get<string>("--output");
    writeOutputFile(fileToWrite, json::object());

    return 0;
}
