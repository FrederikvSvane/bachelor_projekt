#pragma once
#include "../utils/json.hpp"

enum class Sagstype
{
    Straffe,
    Civile,
    Tvang
};

inline void to_json(nlohmann::json& j, const Sagstype& s) {
    switch (s) {
        case Sagstype::Straffe: j = "Straffe"; break;
        case Sagstype::Civile:  j = "Civile";  break;
        case Sagstype::Tvang:   j = "Tvang";   break;
    }
}

inline void from_json(const nlohmann::json& j, Sagstype& s) {
    std::string str = j.get<std::string>();
    if      (str == "Straffe") s = Sagstype::Straffe;
    else if (str == "Civile")  s = Sagstype::Civile;
    else if (str == "Tvang")   s = Sagstype::Tvang;
    else {
        throw std::invalid_argument("Invalid Sagstype string: " + str);
    }
}

