#ifndef appointment_hpp
#define appointment_hpp

#include "judge.hpp"
#include "meeting.hpp"
#include "room.hpp"

struct Appointment {
    Meeting meeting;
    Judge judge;
    Room room;
    int day;
    int timeslot_start;
    int timeslots_duration;

    Appointment(Meeting m, Judge j, Room r, int d, int ts, int td)
        : meeting(m), judge(j), room(r), day(d), timeslot_start(ts), timeslots_duration(td) {}
};

#endif