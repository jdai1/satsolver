from typing import Set, List, Dict


class SATInstance2:
    def __init__(self, num_vars: int, num_clauses: int):
        self.num_vars = num_vars
        self.num_clauses = num_clauses
        self.vars: Set[int] = set()

        self.clauses: List[Set[int]] = []
        self.assignments: Dict[int, bool] = {}

        # Extra data structures

        self.id2clause: Dict[int, Set[int]] = {} # id --> clause
        self.unit_clauses: Set[int] = set() # set of ids of all unit clauses
        self.literal2clause: Dict[int, Set[int]] = {} # literal --> Set of clauses containing literal

    def add_variable(self, literal: int):
        self.vars.add(abs(literal))

    def add_clause(self, clause: Set[int]):
        id_ = id(clause)
        # for any literal, if the negated literal is also present in the clause, it's a tautology
        for l in clause:
            if -l in clause:
                return
            
        if len(clause) == 1:
            self.unit_clauses.add(id_)
        for l in clause:
            if l not in self.literal2clause:
                self.literal2clause[l] = set()
            self.literal2clause[l].add(id_)

        self.id2clause[id_] = clause
        self.clauses.append(clause)

    def assign(self, literal: int):
        self.assignments[abs(literal)] = True if literal > 0 else False

    def __str__(self) -> str:
        result = []
        result.append(f"Number of variables: {self.num_vars}")
        result.append(f"Number of clauses: {self.num_clauses}")
        result.append(f"Variables: {self.vars}")
        
        for c in range(len(self.clauses)):
            result.append(f"Clause {c + 1}: {self.clauses[c]}")
        result.append(f"id2clause: {self.id2clause}")
        result.append(f"unit_clauses: {self.unit_clauses}")
        result.append(f"literal2clause: {self.literal2clause}")
        return "\n".join(result)

    def value(self, literal: int) -> int:
        var = abs(literal)
        if var not in self.assignments:
            return 0
        value = self.assignments[abs(literal)]
        if value:
            return 1 if literal > 0 else -1
        return -1 if literal > 0 else 1

    def check(self) -> bool:
        for _, clause in self.id2clause.items():
            if not any(self.value(l) == 1 for l in clause):
                return False
        return True