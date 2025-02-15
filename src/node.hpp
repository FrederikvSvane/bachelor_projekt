#ifndef node_hpp
#define node_hpp

#include "judge.hpp"
#include "meeting.hpp"
#include "room.hpp"

class Node { // For inheritance og source / sink nodes
  protected:
    int id;
    int color;
    bool visited;

  public:
    Node(int _id) : id(_id), color(-1), visited(false) {}
    virtual ~Node() = default;

    int getId() const { return id; }
    int getColor() const { return color; }
    void setColor(int c) { color = c; }
};

class MeetingNode : public Node {
  private:
    Meeting meeting;

  public:
    MeetingNode(int id, Meeting m) : Node(id), meeting(m) {}

    const Meeting& getMeeting() const { return meeting; }
};

class JudgeRoomNode : public Node {
  private:
    Judge judge;
    Room room;

  public:
    JudgeRoomNode(int id, Judge j, Room r)
        : Node(id), judge(j), room(r) {}

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
        : Node(id), meeting(m), judge(j), room(r) {}

    const Meeting& getMeeting() const { return meeting; }
    const Judge& getJudge() const { return judge; }
    const Room& getRoom() const { return room; }
};

#endif