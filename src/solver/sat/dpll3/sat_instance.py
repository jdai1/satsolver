import time
from functools import wraps
from typing import Set, List, Dict
from dataclasses import dataclass

DEBUG = False


@dataclass
class FunctionStats:
    count: int = 0
    time: float = 0


# UTILS
def track_call_and_time(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.function_stats[func.__name__].count += 1

        start_time = time.time_ns()
        result = func(self, *args, **kwargs)
        end_time = time.time_ns()

        self.function_stats[func.__name__].time += (end_time - start_time) / 1000000000.0

        return result

    return wrapper


def debug_print(msg: str, level: int = 0) -> None:
    if DEBUG:
        space = level * "--"
        space += " " if level != 0 else ""
        print(f"{space}{msg}")


class SATInstance3:
    def __init__(self, num_vars: int, num_clauses: int):
        self.num_vars = num_vars
        self.num_clauses = num_clauses
        self.vars: Set[int] = set()

        self.clauses: List[Set[int]] = []
        self.assignments: Dict[int, bool] = {}
        self.assignment_history: list[int] = []  # stack of literal assignments

        # Extra data structures
        self.id2clause: Dict[int, Set[int]] = {}  # id --> clause
        self.unit_literals: Set[int] = set()
        self.literal2clause: Dict[
            int, Set[int]
        ] = {}  # literal --> Set of clauses containing literal

        # Watched literals
        self.literal2watched: Dict[
            int, Set[int]
        ] = {}  # literal --> Set of clauses that are watching literal
        self.watched2literal: Dict[int, list[int]] = {}  # id --> literals being watched

        # tracking stats
        self.function_stats: dict[str, FunctionStats] = {}
        self.function_stats["assign"] = FunctionStats()
        self.function_stats["unassign"] = FunctionStats()
        self.function_stats["dlcs"] = FunctionStats()
        self.function_stats["has_unit_clause"] = FunctionStats()
        self.function_stats["unit_propagate"] = FunctionStats()

    def add_variable(self, literal: int):
        self.vars.add(abs(literal))

    def add_clause(self, clause: Set[int]):
        assert len(clause)
        id_ = id(clause)

        # for any literal, if the negated literal is also present in the clause, it's a tautology; we can skip adding it
        for l in clause:
            if -l in clause:
                return

        for l in clause:
            if l not in self.literal2clause:
                self.literal2clause[l] = set()
            self.literal2clause[l].add(id_)

        # id2clause
        self.id2clause[id_] = clause

    def setup(self):
        for cid, clause in self.id2clause.items():
            # unit clauses
            if len(clause) == 1:
                only_literal = next(iter(clause))
                self.unit_literals.add(only_literal)
            # len(clause) >= 2
            else:
                c_iter = iter(clause)
                first_literal = next(c_iter)
                second_literal = next(c_iter)

                if first_literal not in self.literal2watched:
                    self.literal2watched[first_literal] = set()
                if second_literal not in self.literal2watched:
                    self.literal2watched[second_literal] = set()

                self.literal2watched[first_literal].add(cid)
                self.literal2watched[second_literal].add(cid)
                self.watched2literal[cid] = [first_literal, second_literal]

    """ Assigns the specified literal to true; updates the watched literal data structures """
    @track_call_and_time
    def assign(self, literal: int, level: int) -> bool:
        var = abs(literal)
        assignment = True if literal > 0 else False

        # Check for existing assignment — if same assignment already exists, we should return
        if var in self.assignments and self.assignments[var] == assignment:
            return False
        
        # Check for conflicts
        if var in self.assignments and self.assignments[var] != assignment:
            return True

        debug_print(f"Assigning {literal} to True", level)
        self.assignments[var] = assignment
        self.assignment_history.append(literal)

        if literal in self.literal2watched:
            for cid in self.literal2watched[literal]:
                # debug_print(str(self.id2clause[cid]), level)
                fl, sl = self.watched2literal[cid]
                fl_value, sl_value = self.value(fl), self.value(sl)
                if fl_value == 1 or sl_value == 1:
                    # debug_print("Clause is already true, leaving literals untouched", level)
                    continue

                # change first watched literal to the propagating literal
                temp = self.watched2literal[cid][0]
                self.watched2literal[cid][0] = literal
                self.literal2watched[temp].remove(cid)
                self.literal2watched[literal].add(cid)
                debug_print(
                    f"Changing first watched literal of {str(self.id2clause[cid])} from {fl} to {literal}",
                    level,
                )

        if -literal in self.literal2watched:
            cids_to_remove_from_literals2watched = []
            for cid in self.literal2watched[-literal]:
                # debug_print(str(self.id2clause[cid]), level)
                fl, sl = self.watched2literal[cid]
                fl_value, sl_value = self.value(fl), self.value(sl)
                if fl_value == 1 or sl_value == 1:
                    # debug_print("Clause is already true, leaving literals untouched", level)
                    continue

                assert not (
                    fl_value == 0 and sl_value == 0
                )  # --> this is a conflict, we should have caught this already!

                new_wl = None
                for l in self.id2clause[cid]:
                    if l != fl and l != sl:
                        if self.value(l) >= 0:  # i.e. l is unassigned or true
                            new_wl = l
                            break

                # add this clause to the unit literal list
                if new_wl is None:
                    debug_print("Unit clause created", level)
                    only_literal = (
                        sl if fl == -literal else fl
                    )  # the unit literal is now the watched literal that did not get set to false
                    self.unit_literals.add(only_literal)
                    continue

                assert new_wl
                if new_wl not in self.literal2watched:
                    self.literal2watched[new_wl] = set()

                if fl == -literal:
                    self.watched2literal[cid][0] = new_wl
                    self.literal2watched[new_wl].add(cid)
                    assert fl == -literal
                    debug_print(
                        f"Changing first watched literal of {str(self.id2clause[cid])} from {fl} to {new_wl}",
                        level,
                    )
                elif sl == -literal:
                    self.watched2literal[cid][1] = new_wl
                    self.literal2watched[new_wl].add(cid)
                    debug_print(
                        f"Changing firsts watched literal of {str(self.id2clause[cid])} from {fl} to {new_wl}",
                        level,
                    )
                cids_to_remove_from_literals2watched.append(cid)

            for cid in cids_to_remove_from_literals2watched:
                self.literal2watched[-literal].remove(cid)

        return False

    """ Backtracks along assignment history until the specified literal has been unassigned """
    @track_call_and_time
    def unassign(self, literal: int, level: int):
        self.unit_literals = set()
        while self.assignment_history:
            literal_to_unassign = self.assignment_history.pop()
            debug_print(f"Unassigning {literal_to_unassign}", level)
            var = abs(literal_to_unassign)
            if var not in self.assignments:
                raise Exception(
                    "tried to unassign literal that was not previously assigned"
                )
            del self.assignments[var]
            if literal_to_unassign == literal:
                break

    """ Based on the current assignments, returns 1 if the literal's value is true, -1 if the value is false, and 0 if it's unassigned"""

    def value(self, literal: int) -> int:
        var = abs(literal)
        if var not in self.assignments:
            return 0
        value = self.assignments[abs(literal)]
        if value:
            return 1 if literal > 0 else -1
        return -1 if literal > 0 else 1

    """ PLE """

    def pure_literal_eliminate(self):
        pure_literals = []
        for l in self.literal2clause:
            if -l not in self.literal2clause:
                pure_literals.append(l)
        print("num pure_literals:", len(pure_literals))
        for pure_literal in pure_literals:
            for cid in self.literal2clause[pure_literal]:
                if cid in self.id2clause:
                    del self.id2clause[
                        cid
                    ]  # delete all clauses that contain the target literal

    @track_call_and_time
    def has_unit_clause(self) -> int:
        if len(self.unit_literals) == 0:
            return 0
        unit_clause_id = next(iter(self.unit_literals))
        clause = self.id2clause[unit_clause_id]
        assert len(clause) == 1
        return next(iter(clause))

    @track_call_and_time
    def unit_propagate(self, level: int) -> bool:
        debug_print(f"Unit literals: {self.unit_literals}", level)
        while self.unit_literals:
            unit_literal = self.unit_literals.pop()
            debug_print(f"Running unit propagation on {unit_literal}", level)

            # Assigns unit_literal to true, checks for conflicts, updates watched2literal and literal2watched
            conflict = self.assign(unit_literal, level)

            if conflict:
                debug_print("Conflict found", level)
                return True
        return False

    # returns the literal used for dlcs
    @track_call_and_time
    def dlcs(self) -> int:
        maxCount = 0
        literal = 0
        for v in self.vars:
            if v in self.assignments:
                continue
            pos_count = 0
            neg_count = 0

            if v in self.literal2watched:
                for cid in self.literal2watched[v]:
                    fl, sl = self.watched2literal[cid]
                    fl_value, sl_value = self.value(fl), self.value(sl)
                    if fl_value != 1 and sl_value != 1:
                        pos_count += 1
            if -v in self.literal2watched:
                for cid in self.literal2watched[-v]:
                    fl, sl = self.watched2literal[cid]
                    fl_value, sl_value = self.value(fl), self.value(sl)
                    if fl_value != 1 and sl_value != 1:
                        neg_count += 1
            if pos_count + neg_count >= maxCount:
                literal = v if pos_count > neg_count else -v
                maxCount = pos_count + neg_count
        return literal

    def is_sat(self) -> bool:
        return len(self.assignments) == len(self.vars)

    def __str__(self) -> str:
        result = []
        result.append(f"Number of variables: {self.num_vars}")
        result.append(f"Number of clauses: {self.num_clauses}")
        result.append(f"Variables: {self.vars}")

        for c in range(len(self.clauses)):
            result.append(f"Clause {c + 1}: {self.clauses[c]}")
        result.append(f"id2clause: {self.id2clause}")
        result.append(f"unit_clauses: {self.unit_literals}")
        return "\n".join(result)

    def check(self) -> bool:
        for _, clause in self.id2clause.items():
            if not any(self.value(l) == 1 for l in clause):
                return False
        return True
