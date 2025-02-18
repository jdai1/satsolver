from .sat_instance import SATInstance3, debug_print
from typing import Set, List, Tuple

DEBUG = False


def dpll_solve3(sat_instance: SATInstance3) -> Tuple[bool, dict[int, bool]]:
    sat_instance.pure_literal_eliminate()
    sat_instance.setup()
    return solve(sat_instance)


def solve(sat_instance: SATInstance3, level: int = 0) -> Tuple[bool, dict[int, bool]]:
    # unit propagation
    conflict = sat_instance.unit_propagate(level)
    if conflict:
        return False, {}

    if sat_instance.is_sat():
        debug_print("All vars are assigned", level)
        return True, sat_instance.assignments

    # splitting
    # random search heuristic
    literal_to_split_on = sat_instance.dlcs()
    sat_instance.assign(literal_to_split_on, level)

    branch_a, assignments = solve(sat_instance, level + 1)
    if branch_a:
        return True, assignments

    sat_instance.unassign(literal_to_split_on, level)
    sat_instance.assign(-literal_to_split_on, level)
    branch_b, assignments = solve(sat_instance, level + 1)
    return branch_b, assignments


"""
Next improvement: using a stack instead of recursion / backtracking manually instead of copying

Currently, recursion is used to split. The cost of this is two fold.
1) recursion is generally expensive compared to iterative approaches


Also:
2) copying datastructures takes more time than remembering the changes you made to them and reapplying them. (i think)

so the goal is to shift to an iterative approach where i use a stack to record changes rather than copying all of my datastuctures.

current data structures im copying
- id2clause (total number of literals across all clauses)
- assignments (total number of variables)
- literal2clause (map from literal to clause, also can't be bigger than total # of clauses)
- unit_clauses (set of integers, can't be bigger than total # of clauses)

is watched literals an absolute gain in time?

unit prop and pure literal elim go to 0 extra work

some overhead associated with assigning a variable (but only in the false case):
- this will be linear time w.r.t to the clause (seems to be 150 at most)
- set some clauses to have a certain watched literal (also is constant relatively).

checking for UNSAT can be done whenever trying to reassing a watched literal. 

what data structures do i need for watched literals?
- assignemnts: dict[int, bool]
- literal to ids of watched clauses: dict[int, set[int]]
- id to clause: dict[int, set[int]]

how does everything change?

- at initialization, i need to find two watched literals for every clause (this can be done in the add_clause function)
- unit prop:
    - happens when there is only one remaining unassigned value in a clause, in which we can imply that it's true
    - assign the literal to a true value, check for conflicts in the current assignment
    - push this assignment onto the stack
    - prioritize true watched literals: in all other clauses that contain this literal, set it to be the watched literal (using literal2clause)
    - for clauses using the negative of the literal as a watched literal: if possible, find another unassigned literal to watch (using )
        if this isn't possible, then do nothing? 
        shouldn't we also check for UNSAT? OR we are also allowed to just let assignments propagate and wait for conflicts to inform us of unsat. we never have to actually check this. 
        the only time i would not be able to find another watched literal is if there is only one unassigned literal left...  in which case I would've already done unit propagation on that one.
        it will never have 0 valid watched literals, b/c this means a conflict will have already occurred.
        we can assume that any clause we check has two valid watched literals. if it did not, then at some point, one of the watched literals was assigned to false, and another one was unable to be found. in that case, we can determine this while trying to find another watched literal and trigger unit prop on it in the next iteration. (keep a set of unit clauses)
        if it only had one left, this means all other variables have been assigned false, and only one is true. so effectivly, anything that would trigger any modifications to the clause would be a conflict.
- pure literals
    - we would still want the pure literal data structure for this...

to check for sat, check that every variable is assigned
        
- dlcs
    - we are only allowed to pick from unassigned variables
"""
