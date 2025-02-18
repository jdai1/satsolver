from .utils import debug_print
from typing import Set, List, Tuple


"""
CDCL Brainstorming:

How does CDCL work?

The thing that differentiates CDCL from DPLL is the concept of clause learning (i.e. adding clauses to the original expression) when conflicts arise.

The basic algorithm is similar, centered around unit propagation. Pure literal elimination is constrained to run only at preprocessing (due to inefficiency?).

1) Deduce --> Determine as many values to assign to a variable as possible:
- First, unit propagation (implied)
- Once there are no more unit literals to propagate, run search heuristic (e.g. VSIDS/DLCS/DLIS) (decided)

- While deduction does not yield a conflict, keep assigning values to new variables by decisions, then implications, decisions, then implications
- If deduction yields a conflict with the existing variable assignments, we run a diagnostic to determine the underlying issue (clause learning).
- If the conflict occurrs at the 0th level of decision (?), then the expression is UNSAT

If there are no more variables to deduce (i.e. all variables have been assigned a value), we've reached a SAT assignment. Return (true, assignment)

How and where do we keep track of the conflicts? (i.e. analyze_conflicts in zChaff code)

We need a way to track which variables were implied by which decisions.
For example:
Store the clause each variable is implied from (antecedent). Suppose at decision level d, a conflict arises. Then, iterate through this clause to find a decision variable with the greatest decision varaible that's less than d. And backtrack to here. Add the clause including all decision variables in the conflict clause as a learned clause. At the backtracked level, the conflicting literal is forced into a propagating literal.

In the context of the implication graph:
UIP: any vertex that all paths that lead from the decision var with the greatest decision variable to the conflict must go through (a vertex that dominates)

UIP Cut: A cut along the graph that separates the into two sets, A and B, where B contains everything along the paths that lead from l to the conflict vertex and A contains everything else.

First UIP (Fast backjumping): the vertex that maximizes the size of the set A. (i.e. the point closest to the conflict vertex that dominates the conflict)

Obvious UIP (Conflict-directed backjumping)

Read MiniSat for a more in-depth explanation of the implementation!

MiniSat Notes:

Main pieces:
- Clause + methods
- Sat instance + methods / state (data structures)
- Watched literals
- Unit propagation
- Analyzing conflict
- Search heuristic (VSIDS)

Extra:
- Restarts
- Constraint removal / ReduceDB

Goal: Create python implementation of MiniSat based on C++ code
Extra: Translate to Rust for performance gains.
"""

