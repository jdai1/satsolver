#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from .parser import DimacsParser
from .utils import Clock
from .cdcl import CDCLSolver
from pprint import pprint
import traceback


def main():
    """Usage example: read a given cnf instance file to create a simple sat instance object and print out its parameter fields."""

    if len(sys.argv) < 2:
        f
        return

    input_file = sys.argv[1]
    filename = Path(input_file).name

    watch = Clock()
    watch.start()

    try:
        instance = DimacsParser.parse_cnf_file(input_file, version=2)
        
        watch.stop()
        print(
            f'{{"Instance": "{filename}", "Time": {watch.get_time():.2f}, "Result": "--"}}'
        )

    except Exception as e:
        traceback.print_exc()
        sys.exit(1)

    assert instance.num_vars > 0
    assert instance.num_clauses > 0

    watch = Clock()
    watch.start()
    sat, assignments = instance.solve() # type: ignore
    watch.stop()

    res = {
        "Instance": filename,
        "Time": f"{watch.get_time():.2f}",
        "Result": "SAT" if sat else "UNSAT",
    }
    if sat:
        assignment_list = []
        for v, a in assignments.items():
            assignment_list.append(str(v))
            assignment_list.append(str(a))
        res["Solution"] = " ".join(assignment_list)
        
    print("Result:", "SAT" if sat else "UNSAT")
    if sat and not instance.check(): # type: ignore
        print("Incorrect assignment")

    pprint(instance.function_stats)
    print("Total time spent in watched functions:", sum([x.time for x in instance.function_stats.values()]))
    print(json.dumps(res))
    


if __name__ == "__main__":
    main()


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

