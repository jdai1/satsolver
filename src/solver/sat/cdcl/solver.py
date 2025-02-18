from attr import dataclass
from typing import Optional, Set, List, Dict
from .utils import debug_print, FunctionStats


class Clause:
    def __init__(self, clause: Set[int], learnt: bool) -> None:
        self.lits = clause
        self.learnt = learnt

        i = iter(clause)
        self.wa = next(i)
        self.wb = next(i)

@dataclass
class VarData:
    cref: Optional[Clause]
    dlevel: int


class CDCLSolver:
    def __init__(self, num_vars: int, num_clauses: int):
        self.num_vars = num_vars
        self.num_clauses = num_clauses
        self.vars: Set[int] = set()

        self.clauses: Set[Clause] = set()               # all clauses
        self.learned_clauses: Set[Clause] = set()       # learned clauses
        self.var_data: Dict[int, VarData] = {}          # data (implication clause + decision level) for each var
        self.assignments: Dict[int, bool] = {}          # variable assignemnts
        self.trail: list[int] = []                      # assignment history
        self.propagation_q: list[int] = []              # queue of literals to propagate
        self.dlevel = 0                                 # decision level

        # Watched literals
        self.literal2watched: Dict[int, Set[Clause]] = {}  # literal --> Set of clauses that are watching literal

        # tracking stats
        self.function_stats: dict[str, FunctionStats] = {}

    def add_variable(self, literal: int):
        self.vars.add(abs(literal))

    def add_clause(self, clause: Set[int], learnt: bool):
        for l in clause:
            if -l in clause:
                return

        if len(clause) == 0:
            return
        if len(clause) == 1:
            self.enqueue(next(iter(clause)))
            self.propagate()
            return

        # len(clause) >= 2
        clause_obj = Clause(clause, learnt=learnt)
        if learnt:
            # TODO: Bump clause activity
            self.learned_clauses.add(clause_obj)
        self.clauses.add(clause_obj)
        self.literal2watched[-clause_obj.wa].add(clause_obj)
        self.literal2watched[-clause_obj.wb].add(clause_obj)

    # PLE, removal of true clauses under current assignment
    def preprocess(self):
        if self.propagate():
            return False
        
        pure_literals = {}
        for c in self.clauses:
            for l in c.lits:
                if -l in pure_literals:
                    pure_literals.pop(l, None)
                    pure_literals.pop(-l, None)

        self.clauses = {c for c in self.clauses for l in c.lits if self.value(l) == 1 or l in pure_literals}
        return True

    def enqueue(self, lit: int, cref: Optional[Clause] = None):
        var = abs(lit)
        assert var not in self.assignments
        self.assignments[var] = True if lit > 0 else False
        self.var_data[var] = VarData(cref=cref, dlevel=self.dlevel)
        self.trail.append(lit)
        self.propagation_q.append(lit)

    def propagate(self) -> Optional[Clause]:
        while self.propagation_q:
            lit = self.propagation_q.pop(0)
            false_lit = -lit
            watched_clauses = self.literal2watched[lit]
            wc_to_remove = []

            # find new watched literal
            for wc in watched_clauses:
                assert false_lit == wc.wa or false_lit == wc.wb
                if (wc.wa == false_lit):  # WLOG, assume that the false watched literal is wc.wb
                    wc.wa = wc.wb
                    wc.wb = false_lit

                if self.value(wc.wa) == 1 or self.value(wc.wb) == 1:
                    continue

                new_watcher_found = False
                for lit in wc.lits:
                    if self.value(lit) >= 0:  # unassigned | True
                        wc.wb = lit
                        self.literal2watched[-wc.wb].add(wc)
                        new_watcher_found = True
                        wc_to_remove.append(wc)  # FIXME: Speed-up
                        break

                if not new_watcher_found:
                    if self.value(wc.wb) == -1:  # conflict
                        assert False
                    else:  # propagate
                        self.enqueue(lit, wc)

            for c in wc_to_remove:
                self.literal2watched[lit].remove(c)

    def backtrackUntil(self, dlevel: int):
        # remove assignments until the specified level & maintain proper dlevel and trail
        while self.dlevel > dlevel:
            lit = self.trail.pop()
            var = abs(lit)
            curr_dlevel = self.var_data[var].dlevel
            del self.assignments[var]
            
            #  TODO: Fudge with "var order"?
            
            if curr_dlevel < self.dlevel:
                self.dlevel = curr_dlevel
 
    def analyze(self, confl: Clause):
        out_learnt_lits = set()
        out_btlevel = 0
        counter = 0
        confl_cl = confl
        seen = {}
        p_lit = None

        while True:
            assert confl_cl
            
            # TODO: Bump clause activity
            
            for l in confl_cl.lits:
                v = abs(l)
                q_var_data = self.var_data[v]
                if v not in seen:
                    # TODO: Bump variable activity 
                    seen[v] = True
                    if q_var_data.dlevel == self.dlevel:
                        counter += 1
                    elif q_var_data.dlevel > 0:
                        out_learnt_lits.add(l)
                        out_btlevel = max(out_btlevel, q_var_data.dlevel)
            while True:
                p_lit = self.trail[-1]
                p_var = abs(p_lit)
                confl_cl = self.var_data[p_var].cref
                if p_var in seen:
                    break
            counter -= 1
            if counter == 0:
                break

        if len(out_learnt_lits) == 0:
            assert out_btlevel == 0
        out_learnt_lits.add(-p_lit)
        return out_btlevel, out_learnt_lits

    def vsids(self) -> int:
        return 0

    def branch_random_lit(self) -> int:
        for v in self.vars:
            if v not in self.assignments:
                return v
        assert False

    def solve(self) -> bool:
        while True:
            confl_cl = self.propagate()
            if confl_cl:
                if self.dlevel == 0:
                    return False
                bt_level, learnt_lits = self.analyze(confl_cl)
                self.backtrackUntil(bt_level)
                self.add_clause(clause=learnt_lits, learnt=True)
                # TODO: Decay activity for var and clauses
            else:
                # TODO: Random restarts
                # TODO: Reduce # learned clauses

                if self.is_sat():
                    return True
                
                if self.dlevel == 0 and not self.preprocess():
                    return False

                # branchLit = self.vsids()
                branchLit = self.branch_random_lit()
                self.dlevel += 1
                self.enqueue(branchLit)
    
    def is_sat(self) -> bool:
        return len(self.assignments) == len(self.vars)

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
            if not any(self.value(l) == 1 for l in clause.lits):
                return False
        return True

    def __str__(self) -> str:
        result = []
        result.append(f"Number of variables: {self.num_vars}")
        result.append(f"Number of clauses: {self.num_clauses}")
        result.append(f"Variables: {self.vars}")
        return "\n".join(result)
