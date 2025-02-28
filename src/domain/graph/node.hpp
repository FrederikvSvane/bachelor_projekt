#pragma once

#include "../judge.hpp"
#include "../meeting.hpp"
#include "../room.hpp"

class Node { // For inheritance og source / sink nodes
  protected:
    int id;
    int color;

  public:
    Node(int _id) : id(_id), color(-1) {}
    virtual ~Node() = default;

    int getId() const { return id; }
    int getColor() const { return color; }
    void setColor(int c) { color = c; }
};

class RoomNode : public Node {
    private:
        Room room;

    public:
        RoomNode(int id, Room r) : Node(id), room(r) {}

        const Room& getRoom() const { return room; }
    };

class JudgeNode : public Node {
    private:
        Judge judge;

    public:
        JudgeNode(int id, Judge j) : Node(id), judge(j) {}

        const Judge& getJudge() const { return judge; }
    };

class MeetingNode : public Node {
  private:
    Meeting meeting;
    int capacity;
    int flow = 0;

  public:
    MeetingNode(int id, int cap, Meeting m) : Node(id), capacity(cap), meeting(m) {}

    int getCapacity() const { return capacity; }
    int getFlow() const { return flow; }
    void setFlow(int f) { flow = f; }
    const Meeting& getMeeting() const { return meeting; }
};

class JudgeRoomNode : public Node {
  private:
    Judge judge;
    Room room;

  public:
    JudgeRoomNode(int id, Judge j, Room r)
        : Node(id), judge(std::move(j)), room(r) {}

    const Judge& getJudge() const { return judge; }
    const Room& getRoom() const { return room; }
};

class MeetingJudgeRoomNode : public Node {
  private:
    Meeting meeting;
    Judge judge;
    Room room;

  public:
    MeetingJudgeRoomNode(int id, Meeting m, Judge j, Room r)
        : Node(id), meeting(m), judge(std::move(j)), room(r) {}

    const Meeting& getMeeting() const { return meeting; }
    const Judge& getJudge() const { return judge; }
    const Room& getRoom() const { return room; }
};

class MeetingJudgeNode : public Node {
  private:
    Meeting meeting;
    Judge judge;

  public:
    MeetingJudgeNode(int id, Meeting m, Judge j)
        : Node(id), meeting(m), judge(std::move(j)) {}

    const Meeting& getMeeting() const { return meeting; }
    const Judge& getJudge() const { return judge; }
};
