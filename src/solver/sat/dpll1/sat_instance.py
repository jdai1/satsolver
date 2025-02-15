from typing import Set, List, Dict


class SATInstance1:
    def __init__(self, num_vars: int, num_clauses: int):
        self.num_vars = num_vars
        self.num_clauses = num_clauses
        self.vars: Set[int] = set()

        self.clauses: List[Set[int]] = []
        self.assignments: Dict[int, bool] = {}

    def add_variable(self, literal: int):
        self.vars.add(abs(literal))

    def add_clause(self, clause: Set[int]):
        # for any literal, if the negated literal is also present in the clause, it's a tautology
        for l in clause:
            if -l in clause:
                return
            
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
        for clause in self.clauses:
            if not any(self.value(l) == 1 for l in clause):
                return False
        return True
