#pragma once
#include "sagstype.hpp"
#include <utility>
#include <vector>
using namespace std;

struct Judge {
    int judge_id;
    vector<Sagstype> judge_skills;
    bool judge_virtual;
    // kan tilføje flere ting her
    Judge(int id, vector<Sagstype> typer, bool virtuel) : judge_id(id), judge_skills(std::move(typer)), judge_virtual(virtuel) {}
};

inline bool judge_has_skill(const Judge& judge, Sagstype skill) {
    for (const auto& s : judge.judge_skills) {
        if (s == skill) {
            return true;
        }
    }
    return false;
}

inline int calculate_judge_capacity(const vector<Meeting>& meetings, const vector<Judge>& judges, int id) {
    int m = get_number_of_sagstyper(); // Total number of case types
    int C = meetings.size();           // Total number of cases
    
    // Get the judge we're calculating for (adjusting for 0-based indexing)
    const Judge& current_judge = judges[id - 1];
    int k = current_judge.judge_skills.size(); // Number of skills this judge has
    
    // Create a map to count meetings by type
    unordered_map<Sagstype, int> cases_by_type;
    for (const auto& meeting : meetings) {
        cases_by_type[meeting.meeting_sagstype]++;
    }
    
    // Calculate weights for all judges for each case type
    unordered_map<Sagstype, int> total_weights_by_type;
    
    // First, initialize weights for all types to 0
    for (const auto& meeting : meetings) {
        if (total_weights_by_type.find(meeting.meeting_sagstype) == total_weights_by_type.end()) {
            total_weights_by_type[meeting.meeting_sagstype] = 0;
        }
    }
    
    // Calculate total weights across all judges for each type
    for (const auto& judge : judges) {
        int judge_skill_count = judge.judge_skills.size();
        for (const auto& skill : judge.judge_skills) {
            total_weights_by_type[skill] += (m - judge_skill_count + 1);
        }
    }
    
    // Calculate this judge's expected case load
    double judge_total_cases = 0.0;
    
    for (const auto& skill : current_judge.judge_skills) {
        // Weight for this judge and case type = (m - k + 1)
        int weight = m - k + 1;
        
        // If there are cases of this type and judges who can handle them
        if (cases_by_type[skill] > 0 && total_weights_by_type[skill] > 0) {
            // Proportion of this type's cases this judge should handle
            double proportion = static_cast<double>(weight) / total_weights_by_type[skill];
            
            // Number of cases of this type this judge should handle
            judge_total_cases += proportion * cases_by_type[skill];
        }
    }
    
    // Convert to integer capacity (round to nearest integer)
    int capacity = static_cast<int>(round(judge_total_cases));
    
    // Ensure capacity is at least 1 if this judge has any applicable skills
    if (capacity < 1 && k > 0) {
        capacity = 1;
    }
    
    return capacity;
}