#pragma once

#include "sagstype.hpp"

struct  Meeting
{
    int meeting_id;
    int meeting_duration;
    Sagstype meeting_sagstype;
    bool meeting_virtual;
    Meeting(int id, int duration, Sagstype type, bool virtuel) : meeting_id(id), meeting_duration(duration), meeting_sagstype(type), meeting_virtual(virtuel) {}
};
