#pragma once
using namespace std;

struct Room {
    int room_id;
    bool room_virtual;

    Room(int id, bool virtuel) : room_id(id), room_virtual(virtuel) {}
};
