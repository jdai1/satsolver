from sat_instance import SATInstance
from typing import Set, List, Tuple

DEBUG = False


def dpll_solve(
    sat_instance: SATInstance, level: int = 0
) -> Tuple[bool, dict[int, bool]]:
    # unit propagation
    while True:
        l = has_unit_clause(sat_instance.clauses)  # NOTE
        if not l:  # l = 0
            break
        debug_print(f"Running unit propagation on {l}", level)
        sat_instance.assign(l)  # assign l to true
        empty_clause_found, new_clauses = unit_propagate(
            l, sat_instance.clauses
        )  # NOTE
        if empty_clause_found:
            return False, {}
        sat_instance.clauses = new_clauses

    # pure literal elimination
    while True:
        l = has_pure_literal(sat_instance.clauses)  # NOTE
        if not l:  # l = 0
            break
        debug_print(f"Running literal elimination on {l}", level)
        sat_instance.assign(l)  # assign l to true
        sat_instance.clauses = literal_eliminate(l, sat_instance.clauses)  # NOTE

    if len(sat_instance.clauses) == 0:
        debug_print("Clauses list is empty (SAT)", level)
        return True, sat_instance.assignments

    # splitting
    # random search heuristic
    random_assignment = next(iter(sat_instance.clauses[0]))
    debug_print(f"Recurring with {random_assignment} set to True", level)

    old_assignments = sat_instance.assignments
    new_assignments = {k: v for k, v in sat_instance.assignments.items()}
    sat_instance.assignments = new_assignments
    sat_instance.assign(random_assignment)

    old_clauses = sat_instance.clauses
    new_clauses = [c.copy() for c in sat_instance.clauses]
    sat_instance.clauses = new_clauses
    sat_instance.add_clause({random_assignment})

    branch_a, assignments = dpll_solve(sat_instance, level + 1)
    if branch_a:
        return True, assignments

    sat_instance.assignments = old_assignments
    sat_instance.assign(-random_assignment)

    sat_instance.clauses = old_clauses
    sat_instance.add_clause({-random_assignment})

    debug_print(f"Recurring with {random_assignment} set to False", level)
    branch_b, assignments = dpll_solve(sat_instance, level + 1)

    if branch_b:
        return branch_b, assignments
    return branch_b, {}


def has_unit_clause(clauses: List[Set[int]]) -> int:
    for c in clauses:
        if len(c) == 1:
            return next(iter(c))
    return 0


def unit_propagate(
    literal: int, clauses: List[Set[int]]
) -> Tuple[bool, List[Set[int]]]:
    new_clauses = []
    for c in clauses:
        if literal in c:
            continue
        if -literal in c:
            c.remove(-literal)  # NOTE
            if len(c) == 0:
                return True, []
        new_clauses.append(c)
    return False, new_clauses


def has_pure_literal(clauses: List[Set[int]]) -> int:
    literal_counter = {}
    for c in clauses:
        for l in c:
            if l not in literal_counter:
                literal_counter[l] = 0
            literal_counter[l] += 1
    literal = 0
    for l in literal_counter:
        if -l not in literal_counter:
            literal = l
            break
    return literal


def literal_eliminate(literal: int, clauses: List[Set[int]]) -> List[Set[int]]:
    new_clauses = []
    for c in clauses:
        if literal in c:
            continue
        new_clauses.append(c)
    return new_clauses


def debug_print(msg: str, level: int = 0) -> None:
    if DEBUG:
        space = level * "--"
        space += " " if level != 0 else ""
        print(f"{space}{msg}")
