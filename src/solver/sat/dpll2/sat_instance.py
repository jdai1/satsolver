from typing import Set, List, Dict
import time
from dataclasses import dataclass
from functools import wraps
import random

DEBUG = False

@dataclass
class FunctionStats:
    count: int = 0
    time: float = 0


# UTILS

def debug_print(msg: str, level: int = 0) -> None:
    if DEBUG:
        space = level * "--"
        space += " " if level != 0 else ""
        print(f"{space}{msg}")


def track_call_and_time(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.function_stats[func.__name__].count += 1

        start_time = time.time()
        result = func(self, *args, **kwargs)
        end_time = time.time()

        self.function_stats[func.__name__].time += end_time - start_time

        return result

    return wrapper

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

        # tracking stats
        self.function_stats: dict[str, FunctionStats] = {}
        self.function_stats["add_clause"] = FunctionStats()
        self.function_stats["assign"] = FunctionStats()
        self.function_stats["dlcs"] = FunctionStats()
        self.function_stats["dlis"] = FunctionStats()
        self.function_stats["randomized_dlis"] = FunctionStats()
        self.function_stats["randomized_dlcs"] = FunctionStats()
        self.function_stats["has_unit_clause"] = FunctionStats()
        self.function_stats["unit_propagate"] = FunctionStats()
        self.function_stats["has_pure_literal"] = FunctionStats()
        self.function_stats["literal_eliminate"] = FunctionStats()
        self.function_stats["copy"] = FunctionStats()

    def add_variable(self, literal: int):
        self.vars.add(abs(literal))

    @track_call_and_time
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

    @track_call_and_time
    def assign(self, literal: int):
        self.assignments[abs(literal)] = True if literal > 0 else False

    @track_call_and_time
    def has_unit_clause(self) -> int:
        if len(self.unit_clauses) == 0:
            return 0
        unit_clause_id = next(iter(self.unit_clauses))
        clause = self.id2clause[unit_clause_id]
        assert len(clause) == 1
        return next(iter(clause))

    @track_call_and_time
    def unit_propagate(self, literal: int, level: int) -> bool:
        # delete all clauses that contain the target literal
        for cid in self.literal2clause[literal]:
            if cid in self.unit_clauses: # update unit_clauses
                self.unit_clauses.remove(cid)
            for l in self.id2clause[cid]: # udpate literal2clause
                if l != literal:
                    self.literal2clause[l].remove(cid)
            debug_print(f"Removing {cid} from id2clause", level)
            del self.id2clause[cid]  # remove clause

        debug_print(f"Removing {literal} from literal2clause", level)

        # nuke literal entry from literal2clause
        del self.literal2clause[literal]

        # remove the literal from any clauses that contain the negation of the target literal
        if -literal in self.literal2clause:
            for cid in self.literal2clause[-literal]:
                clause = self.id2clause[cid]
                clause.remove(-literal)  # remove -literal from clause
                if len(clause) == 0: # unsat condition
                    assert cid in self.unit_clauses
                    return True
                if len(clause) == 1: # update unit clauses
                    self.unit_clauses.add(cid)

            debug_print(f"Removing {-literal} from literal2clause", level)
            
            # nuke -literal entry from literal2clause
            del self.literal2clause[-literal]

        return False


    # returns first pure literal it finds... same behavior as before, but faster, since we don't need to count them each time
    @track_call_and_time
    def has_pure_literal(self) -> int:
        for l in self.literal2clause:
            if len(self.literal2clause[l]) == 0:
                continue
            if -l not in self.literal2clause or len(self.literal2clause[-l]) == 0:
                return l
        return 0

    # literal elimination
    @track_call_and_time
    def literal_eliminate(self, literal: int, level: int):
        for cid in self.literal2clause[literal]:
            for l in self.id2clause[cid]: # udpate literal2clause
                if l != literal:
                    self.literal2clause[l].remove(cid)
                    
            debug_print(f"Removing {cid} from id2clause", level)
            del self.id2clause[cid]  # delete all clauses that contain the target literal
            
        del self.literal2clause[literal]  # nuke target literal entry from literal2clause

    # returns the literal used for dlcs
    @track_call_and_time
    def dlcs(self) -> int:
        top1 = (0, None)
        for l in self.literal2clause:
            pos_count = len(self.literal2clause[l])
            neg_count = len(self.literal2clause[-l]) if -l in self.literal2clause else 0
            count = pos_count + neg_count
            if count > top1[0]:
                top1 = (count, l)
        assert top1[1]
        literal = top1[1]
        pos_count = len(self.literal2clause[literal])
        neg_count = len(self.literal2clause[-literal]) if -literal in self.literal2clause else 0
        return literal if pos_count > neg_count else -literal

    # returns the literal used for dlcs
    @track_call_and_time
    def randomized_dlcs(self) -> int:
        top1 = (0, None)
        top2 = (0, None)
        top3 = (0, None)

        for l in self.literal2clause:
            pos_count = len(self.literal2clause[l])
            neg_count = len(self.literal2clause[-l]) if -l in self.literal2clause else 0
            count = pos_count + neg_count
            if count > top1[0]:
                top3 = top2
                top2 = top1
                top1 = (count, l)
            elif count > top2[0]:
                top3 = top2
                top2 = (count, l)
            elif count > top3[0]:
                top3 = (count, l)
                
        assert top1[1] and top2[1] and top3[1]
        top3_literals = [top1[1], top2[1], top3[1]]
        literal = random.choice(top3_literals)
        pos_count = len(self.literal2clause[literal])
        neg_count = len(self.literal2clause[-literal]) if -literal in self.literal2clause else 0
        return literal if pos_count > neg_count else -literal


    @track_call_and_time
    def dlis(self) -> int:
        assert 0 not in self.literal2clause
        top1 = (0, None)

        for l in self.literal2clause:
            count = len(self.literal2clause[l])
            if count > top1[0]:
                top1 = (count, l)
        assert top1[1]
        return top1[1]
    

    # returns the literal used for dlcs
    @track_call_and_time
    def randomized_dlis(self) -> int:
        assert 0 not in self.literal2clause
        top1 = (0, None)
        top2 = (0, None)
        top3 = (0, None)

        for l in self.literal2clause:
            count = len(self.literal2clause[l])
            if count > top1[0]:
                top3 = top2
                top2 = top1
                top1 = (count, l)
            elif count > top2[0]:
                top3 = top2
                top2 = (count, l)
            elif count > top3[0]:
                top3 = (count, l)
                
        assert top1[1] and top2[1] and top3[1]
        top3_literals = [top1[1], top2[1], top3[1]]
        return random.choice(top3_literals)
    

    @track_call_and_time
    def copy(self):
        old_assignments = self.assignments
        new_assignments = {k: v for k, v in self.assignments.items()}
        self.assignments = new_assignments

        old_literal2clause = self.literal2clause
        new_literal2clause = {
            literal: set(cids) for literal, cids in self.literal2clause.items()
        }
        self.literal2clause = new_literal2clause

        old_unit_clauses = self.unit_clauses
        new_unit_clauses = set(self.unit_clauses)
        self.unit_clauses = new_unit_clauses

        old_id2clause = self.id2clause
        new_id2clause = {cid: set(c) for cid, c in self.id2clause.items()}
        self.id2clause = new_id2clause

        return old_assignments, old_literal2clause, old_unit_clauses, old_id2clause

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