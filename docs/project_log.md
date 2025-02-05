# Log of meetings and decisions

- 7. November 2024:

Met with department responsible Martin Buur at Domsstolsstyrelsen to pitch idea of working on the court case scheduling problem as a bachelor project. He was keen on the idea and told us that they would like to collaborate.


- 15. November 2024

Met with Martin Buur and developer Christian Jørck to talk feasibility, scope and the different potential problems to work on within their court case scheduling problem.
Also made an agreement to have Christian Jørck as supervisor from Domstolsstyrelsen.


- 26. November 2024

Met with potential project supervisor from DTU, Anne Haxthausen.
She said yes to be our supervisor, but at the same time recommended that we find someone else to supervise, because scheduling problems are out of her expertise.


- 18. December 2024

Met with other potential project supervisors Philip Bille and Inge Gøtz at DTU. They would also like to supervise us, and said that the problem is in fact wihtin their expertise.
But they told us to talk with our supervisor from Domstolsstyrelsen to come up with a concrete problem specification.


- 14. January 2025

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



