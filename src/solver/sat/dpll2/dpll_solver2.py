from .sat_instance import SATInstance2, debug_print
from typing import Set, List, Tuple

def dpll_solve2(
    sat_instance: SATInstance2, level: int = 0
) -> Tuple[bool, dict[int, bool]]:
    # unit propagation
    while True:
        l = sat_instance.has_unit_clause()
        if not l:  # l = 0
            break
        debug_print(f"Running unit propagation on {l}", level)
        sat_instance.assign(l)  # assign l to true
        empty_clause_found = sat_instance.unit_propagate(l, level)  # NOTE
        if empty_clause_found:
            debug_print("Empty clause found during unit prop", level)
            return False, {}

    # pure literal elimination
    while True:
        l = sat_instance.has_pure_literal()
        if not l:  # l = 0
            break
        debug_print(f"Running literal elimination on {l}", level)
        sat_instance.assign(l)  # assign l to true
        sat_instance.literal_eliminate(l, level)

    if len(sat_instance.id2clause) == 0:
        debug_print("Clauses list is empty (SAT)", level)
        return True, sat_instance.assignments

    # splitting
    # random search heuristic
    dlcs_out = sat_instance.randomized_dlcs()
    debug_print(f"Recurring with {dlcs_out} set to True", level)

    old_assignments, old_literal2clause, old_unit_clauses, old_id2clause = sat_instance.copy()
    sat_instance.assign(dlcs_out)
    sat_instance.add_clause({dlcs_out})

    branch_a, assignments = dpll_solve2(sat_instance, level + 1)
    if branch_a:
        return True, assignments

    sat_instance.assignments = old_assignments
    sat_instance.unit_clauses = old_unit_clauses
    sat_instance.literal2clause = old_literal2clause
    sat_instance.id2clause = old_id2clause
    
    sat_instance.assign(-dlcs_out)
    sat_instance.add_clause({-dlcs_out})

    debug_print(f"Recurring with {dlcs_out} set to False", level)
    branch_b, assignments = dpll_solve2(sat_instance, level + 1)

    if branch_b:
        return branch_b, assignments
    return branch_b, {}

""" NOTES """

# NOTE: A map from # literals --> clause would be nice!. Then we would need an id for each clause. Since clauses are regularly added and deleted, we would want a unqiue ID for each clause that's not just it's position in the list. So then we'd need a map from ID to clause? Iterating through this would be effectively the same as iterating through a list of sets.

# Let's first think about the map from ID to clause. How would this work during initialization?

# We could have have each clause map to a unique ID that is increased by 1. or use the id() function?
# We could also then create a map from length of clause to a list (or hashset would be faster) of the IDs of the clauses of that length (this would improve efficiency for has_unit_clause)

# in unit propagate, we could modify both dictionaries in place w/ no added time complexity. but we'd have to modify length --> to clause any time we updated, added, or removed a clause

# does not affect has_pure_literal... in order to increase speed of this we could keep another dict mapping literal to count. we would have to update this any time we updated, added, or removed a clause

# unit prop and literal elim would both benefit from having a map from literal to id of clause that contains this literal. call this literal --> id. having this dict would allow a faster removal. (we can directly remove each clause in O(1) time instead of having to iterate. in unit prop we can also directly update each clause with negative literal directly.)

# ok lets summarize. the proposed datastructures (all dictionaries) are:

"""
1. updating clauses field in sat_assignment: id (int) --> clause (set)
2. set of clauses that are of length 1 --> set of ids of clauses that are unit (hashset)
3. literal (int) --> set of ids of clauses that contain this literal (hashset ~ dict)

n = number of clauses
l = number of literals (at most 2x number of variables, v)
#2 would speed up unit prop --> we can immediately determine any clauses to initiate unit prop on, improving speed from O(n) to O(1)
#3 would let us find pure literals in O(l) instead of O(n). 
# Is there any way we can make this O(1)? we could do this if we keep a running set of pure literals... essentially anytime we add, update, or delete a clause, we'd have to update this

#2 and #3 would necessitate having #1, which would be the id of the clause mapped to the actual clause itself.

#1, #2, and #3 would all need to be updated whenever any clause is added, updated, or deleted

where are clauses added?
- splitting --> we need to update #1 by adding a new id, update #2 by adding a new entry, update #3 by adding a the new id to corresponding hashset value. O(1)
- however we also need to create copies of all of #1, #2, and #3 on splitting. we are already copying for #1. #2 we can assume will be pretty small, and #3 should be at most as large as #1. So we are incurring an extra cost of at most O(n) here.

where are clauses updated?
- unit prop (with negated literals) --> if post-update clause is now length 1, we add it. if length 0 we return False here. update #3 by removing by nuking the corresponding entry for the negated literal (since they are all removed!) this is O(1)

question: do we actually only need to keep track of clauses that are length one??? this makes our lives easier i think... A: Yes.

where are clauses deleted?
- unit prop --> update #1 by deleting id. update #2 by removing id if inside (but there shouldn't be if we do unit prop first). update #3 by looping through clause and removing id from all necessary entries (i.e. the literals that are inside the clause). this should be pretty small b/c # of literals shouldn't be that big. basically O(1)

- pure literal elim --> same as above. ^ also basically O(1)

What time are we saving?

- we can do has_unit_clause in O(1) time from O(n)
- we can do unit propagation in O(l) from O(n) where l is the sum of all literals in the clauses we need to eliminate
- we can check pure_literal conditions in O(l) from O(n) + O(l). i.e. loop through and for each variable, check the negated variable to see if it exists
- we can perform literal elim in O(l) from O(n) where l is sum of all literals in the clauses we need to eliminate

so we r saving net time. added cost of at most O(n) when copying but reducing by 2O(n) and change

also we can DLCS (dynamic largest combined sum) heuristic in O(1) with #3

"""


"""
Next improvement: using a stack instead of recursion

Currently, recursion is used to split. The cost of this is two fold.
1) recursion is generally expensive compared to iterative approaches
2) copying datastructures takes more time than remembering the changes you made to them and reapplying them. (i think)

so the goal is to shift to an iterative approach where i use a stack to record changes rather than copying all of my datastuctures.

current data structures im copying
- id2clause (total number of literals across all clauses)
- assignments (total number of variables)
- literal2clause (map from literal to clause, also can't be bigger than total # of clauses)
- unit_clauses (set of integers, can't be bigger than total # of clauses)

if i did recursion? 
"""
