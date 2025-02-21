#pragma once

#include <string>
#include "argparse.hpp"
#include "json.hpp"
#include <fstream>
#include <iostream>

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
        std::cerr << "Argument parsing error: " << e.what() << std::endl;
        exit(1);
    }
}

inline void writeOutputFile(const std::string &filename, const nlohmann::json &output_json) {
    std::ofstream out_file(filename);
    if (!out_file.is_open()) {
        std::cerr << "Error opening output file: " << filename << "\n";
        exit(1);
    }
    out_file << output_json.dump(4);
    out_file.close();
}