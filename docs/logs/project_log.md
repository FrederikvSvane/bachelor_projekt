# Log of meetings and decisions

## 7. November 2024:

Met with department responsible Martin Buur at Domsstolsstyrelsen to pitch idea of working on the court case scheduling problem as a bachelor project. He was keen on the idea and told us that they would like to collaborate.


## 15. November 2024

Met with Martin Buur and developer Christian Jørck to talk feasibility, scope and the different potential problems to work on within their court case scheduling problem.
Also made an agreement to have Christian Jørck as supervisor from Domstolsstyrelsen.


## 26. November 2024

Met with potential project supervisor from DTU, Anne Haxthausen.
She said yes to be our supervisor, but at the same time recommended that we find someone else to supervise, because scheduling problems are out of her expertise.


## 18. December 2024

Met with other potential project supervisors Philip Bille and Inge Gøtz at DTU. They would also like to supervise us, and said that the problem is in fact wihtin their expertise.
But they told us to talk with our supervisor from Domstolsstyrelsen to come up with a concrete problem specification.


## 14. January 2025

Met with Christian Jørck to formulate a concrete problem.
We decided upon the following:

Core objectives:

    Write algorithm to schedule court cases
    Start with a simple, but easily expandable MVP

The solution will use:

    Open source rule engine library for evaluating proposed solution (instead of reinventing the wheel)
    Local search and heuristics for optimization
    Data model for courts, meetings, and judges
    Hard constraints (no double bookings, capacity requirements)
    Soft constraints (minimizing room changes, preferred rooms)

## 7. Februar 2025:

Met with Philip and Inge.
We presented the semi concrete problem description that we worked out with Christian Jørck, and they liked it.
So they agreed to be our supervisors.
They shared a folder of documents for us to use and fill out. Specifically we need to write a problem description text and fill out a project template before the next meeting on 25. februar 2025.

## 12. February 2025

Made a first version of how to model our mvp. Consisting of scheduling meetings, court rooms and judges, in as few timeslots as possible.

The general idea will be:

    Initial construction of cases, with judges, court_rooms and  meetings, solved via bipartite maxing. From here on applying a graph coloring algorithm (DSatur) so put the meetings into as few timeslots as possible.

## 14. February 2025

Prepared everything for first meeting.

## 19. February 2025

Spent entire day developing core foundation for graph solution, and a over-simplified graph representation.

## 21. February 2025

Used for final touches for first meeting and improving the structure of the project




