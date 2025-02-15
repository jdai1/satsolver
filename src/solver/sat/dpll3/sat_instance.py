from typing import Set, List, Dict

DEBUG = False

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

        # Watched literals
        self.literal2watched: Dict[int, Set[int]] = {}  # literal --> Set of clauses that are watching literal
        self.watched2literal: Dict[int, list[int]] = {}  # id --> literals being watched

    def add_variable(self, literal: int):
        self.vars.add(abs(literal))

    def add_clause(self, clause: Set[int]):
        assert len(clause)
        id_ = id(clause)

        # for any literal, if the negated literal is also present in the clause, it's a tautology; we can skip adding it
        for l in clause:
            if -l in clause:
                return

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

            self.literal2watched[first_literal].add(id_)
            self.literal2watched[second_literal].add(id_)
            self.watched2literal[id_] = [first_literal, second_literal]

        # id2clause
        self.id2clause[id_] = clause
        self.clauses.append(clause)

    """ Assigns the specified literal to true; updates the watched literal data structures """

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
                debug_print(f"Changing first watched literal of {str(self.id2clause[cid])} from {fl} to {literal}", level)

        if -literal in self.literal2watched:
            cids_to_remove_from_literals2watched = []
            for cid in self.literal2watched[-literal]:
                # debug_print(str(self.id2clause[cid]), level)
                fl, sl = self.watched2literal[cid]
                fl_value, sl_value = self.value(fl), self.value(sl)
                if fl_value == 1 or sl_value == 1:
                    # debug_print("Clause is already true, leaving literals untouched", level)
                    continue

                assert not (fl_value == 0 and sl_value == 0) # --> this is a conflict, we should have caught this already!
                
                new_wl = None
                for l in self.id2clause[cid]:
                    if l != fl and l != sl:
                        if self.value(l) >= 0: # i.e. l is unassigned or true
                            new_wl = l
                            break
                
                # add this clause to the unit literal list
                if new_wl is None:
                    debug_print("Unit clause created", level)
                    only_literal = sl if fl == -literal else fl # the unit literal is now the watched literal that did not get set to false
                    self.unit_literals.add(only_literal)
                    continue
                
                assert new_wl
                if new_wl not in self.literal2watched:
                    self.literal2watched[new_wl] = set()
                    
                if fl == -literal:
                    self.watched2literal[cid][0] = new_wl
                    self.literal2watched[new_wl].add(cid)
                    assert fl == -literal
                    debug_print(f"Changing first watched literal of {str(self.id2clause[cid])} from {fl} to {new_wl}", level)
                elif sl == -literal:
                    self.watched2literal[cid][1] = new_wl
                    self.literal2watched[new_wl].add(cid)
                    debug_print(f"Changing firsts watched literal of {str(self.id2clause[cid])} from {fl} to {new_wl}", level)
                cids_to_remove_from_literals2watched.append(cid)
                
            for cid in cids_to_remove_from_literals2watched:
                self.literal2watched[-literal].remove(cid)

        return False

    """ Backtracks along assignment history until the specified literal has been unassigned """

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


def debug_print(msg: str, level: int = 0) -> None:
    if DEBUG:
        space = level * "--"
        space += " " if level != 0 else ""
        print(f"{space}{msg}")