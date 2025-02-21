#pragma once
struct  Meeting
{
    int meeting_id;
    int meeting_duration;
    // duration i fremtiden
    Meeting(int id, int duration) : meeting_id(id), meeting_duration(duration) {}
};
