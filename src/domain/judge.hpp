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