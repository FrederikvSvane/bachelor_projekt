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
#include <iostream>

using json = nlohmann::json;
using namespace std;
namespace fs = std::filesystem;

// Inline function to parse command-line arguments
inline void parseArguments(int argc, char const *argv[], argparse::ArgumentParser &program) {
    program.add_argument("-i", "--input")
            .help("Path to the input JSON file")
            .default_value(std::string(""));
    program.add_argument("-o", "--output")
            .help("Path to the output JSON file")
            .default_value(std::string("output.json"));
    program.add_argument("--test")
            .help("Use the test input file")
            .default_value(false)
            .implicit_value(true);

    try {
        program.parse_args(argc, argv);
    } catch (const std::exception &e) {
        cerr << "Argument parsing error: " << e.what() << endl;
        exit(1);
    }
}

// Inline function to write schedule output to a file
inline void writeOutputFile(const std::string &filename, const json &output_json) {
    ofstream out_file(filename);
    if (!out_file.is_open()) {
        cerr << "Error opening output file: " << filename << "\n";
        exit(1);
    }
    out_file << output_json.dump(4);
    out_file.close();
}

int main(int argc, char const *argv[]) {
    argparse::ArgumentParser program("CourtCaseScheduler");
    parseArguments(argc, argv, program);

    auto fileToWrite = program.get<string>("--output");

    parser::ParsedData parsed_data;
    if (!parseInputFile(program, parsed_data, false)) {
        return 1;
    }

    Schedule schedule = generateSchedule(parsed_data);
    schedule.visualize();

    writeOutputFile(fileToWrite, json::object());

    return 0;
}

