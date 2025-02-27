from attr import dataclass
from typing import Optional, Set, List, Dict
import heapq
from .utils import debug_print, FunctionStats

class VSIDSHeap:
    def __init__(self, decay_factor=0.95):
        self.heap = []
        self.decay_factor = decay_factor
        self.var_inc = 1

    def push(self, lit: int, score):
        heapq.heappush(self.heap, (score, lit))

    def pop(self):
        if not self.heap:
            raise Exception()
        score, item = heapq.heappop(self.heap)
        return item, score

    def decay_scores(self):
        self.var_inc *= (1 / self.decay_factor)

    def update_score(self, item):
        for i in range(len(self.heap)):
            if self.heap[i][1] == item:
                self.heap[i] = (self.heap[i][0] + self.var_inc, item)
                heapq.heapify(self.heap)
                break


class Clause:
    def __init__(self, clause: Set[int], learnt: bool) -> None:
        self.lits = clause
        self.learnt = learnt

        i = iter(clause)
        self.wa = next(i)
        self.wb = next(i)

    def __str__(self) -> str:
        return f"{self.lits}"

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

        # VSIDS
        self.activity = VSIDSHeap()
        self.polarity = {}

        # tracking stats
        self.function_stats: dict[str, FunctionStats] = {}

    def add_variable(self, literal: int):
        self.activity.push(abs(literal), 0)
        self.polarity[abs(literal)] = 0
        self.vars.add(abs(literal))

    def add_clause(self, clause: Set[int], learnt: bool = False) -> Optional[Clause]:
        debug_print(f"Adding a {'learned ' if learnt else ''}clause: {clause}", self.dlevel)
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
        if -clause_obj.wa not in self.literal2watched:
            self.literal2watched[-clause_obj.wa] = set()
        if -clause_obj.wb not in self.literal2watched:
            self.literal2watched[-clause_obj.wb] = set()
            
        self.literal2watched[-clause_obj.wa].add(clause_obj)
        self.literal2watched[-clause_obj.wb].add(clause_obj)

        return clause_obj

    # PLE, removal of true clauses under current assignment
    def preprocess(self):
        debug_print("Calling preprocess...", self.dlevel)
        assert self.dlevel == 0
        
        if self.propagate():
            return False
        
        literal2clause = {}
        for c in self.clauses:
            for l in c.lits:
                if l not in literal2clause:
                    literal2clause[l] = set()
                literal2clause[l].add(c)
                
        # TODO: Speed-up!
        for l in literal2clause:
            if -l not in literal2clause:
                # easier just to assign manually, rather than using enqueue (since we are gauranteed to be at level 0 here)
                self.enqueue(l)

        # TODO: Speed-up!
        new_clauses = set()
        for c in self.clauses:
            if not self.is_clause_sat(c):
                new_clauses.add(c)
        self.clauses = new_clauses
        return True

    def enqueue(self, lit: int, cref: Optional[Clause] = None):
        debug_print(f"Calling enqueue with {lit}", self.dlevel)
        var = abs(lit)
        self.assignments[var] = True if lit > 0 else False
        self.var_data[var] = VarData(cref=cref, dlevel=self.dlevel)
        self.trail.append(lit)
        self.propagation_q.append(lit)

    def propagate(self) -> Optional[Clause]:
        debug_print(f"Calling propagate with prop q: {self.propagation_q}", self.dlevel)
        while self.propagation_q:
            prop_lit = self.propagation_q.pop(0)
            debug_print(f"Propagating {prop_lit}", self.dlevel)
            
            false_prop_lit = -prop_lit
            if prop_lit not in self.literal2watched: # no clauses are watching the negated propagating literal
                continue
                
            watched_clauses = self.literal2watched[prop_lit]
            wc_to_remove = []

            # find new watched literal
            for wc in watched_clauses:
                debug_print(f"Watched clause: {wc}", self.dlevel)
                debug_print(f"W1: {wc.wa}; W2: {wc.wb}", self.dlevel)
                assert false_prop_lit == wc.wa or false_prop_lit == wc.wb
                if (wc.wa == false_prop_lit):  # WLOG, assume that the false watched literal is wc.wb
                    wc.wa = wc.wb
                    wc.wb = false_prop_lit

                if self.value(wc.wa) == 1 or self.value(wc.wb) == 1:
                    continue

                new_watcher_found = False
                for lit in wc.lits:
                    if lit != wc.wb and lit != wc.wa and self.value(lit) >= 0:  # unassigned | True
                        wc.wb = lit
                        if -wc.wb not in self.literal2watched:
                            self.literal2watched[-wc.wb] = set()
                        self.literal2watched[-wc.wb].add(wc)
                        new_watcher_found = True
                        wc_to_remove.append(wc)  # FIXME: Speed-up
                        debug_print(f"Found new watched literal {lit}", self.dlevel)
                        break

                if not new_watcher_found:
                    if self.value(wc.wa) == -1:  # conflict
                        debug_print(f"Conflict identified: {wc} is False", self.dlevel)
                        for c in wc_to_remove:
                            self.literal2watched[prop_lit].remove(c)
                        return wc
                    else:  # propagate
                        self.enqueue(wc.wa, wc)

            for c in wc_to_remove:
                self.literal2watched[prop_lit].remove(c)

    def backtrackUntil(self, dlevel: int):
        debug_print(f"Calling backtrack until level {dlevel}...", self.dlevel)
        debug_print(f"Trail: {self.trail}", self.dlevel)
        # remove assignments until the specified level & maintain proper dlevel and trail
        while self.dlevel > dlevel:
            if dlevel == 0 and not self.trail:
                self.dlevel = 0
                break
            lit = self.trail[-1]
            var = abs(lit)
            curr_dlevel = self.var_data[var].dlevel
            self.dlevel = curr_dlevel
            
            debug_print(f"Var: {var}, Level: {curr_dlevel}", self.dlevel)
            
            #  TODO: Fudge with "var order"?
            if self.dlevel > dlevel:
                del self.assignments[var]
                self.trail.pop()
                self.activity.push(lit, 0)
                if self.propagation_q:
                    assert lit == self.propagation_q.pop()
            else:
                break

        # TODO: Propagation queue! need to update this/.
        debug_print(f"New assignments: {self.assignments}", self.dlevel)
        debug_print(f"New trail: {self.trail}", self.dlevel)
        debug_print(f"New prop q: {self.propagation_q}", self.dlevel)
 
    def analyze(self, confl: Clause):
        debug_print(f"Calling analyze on {confl.lits}", self.dlevel)
        out_learnt_lits = set()
        counter = 0
        confl_cl = confl
        seen = {}
        p_lit = None
        bt_count = 0

        while True:
            assert confl_cl
            
            # TODO: Bump clause activity
            debug_print(f"Conflict Clause: {confl_cl.lits}, P_lit: {p_lit}", self.dlevel)
            for l in confl_cl.lits:
                v = abs(l)
                q_var_data = self.var_data[v]
                if v not in seen:
                    # TODO: Bump variable activity 
                    self.activity.update_score(v)
                    seen[v] = True
                    if q_var_data.dlevel >= self.dlevel:
                        counter += 1
                    elif q_var_data.dlevel > 0:
                        out_learnt_lits.add(l)
            while True:
                p_lit = self.trail[-1 - bt_count]
                bt_count += 1
                p_var = abs(p_lit)
                confl_cl = self.var_data[p_var].cref
                if p_var in seen:
                    break
            counter -= 1
            if counter <= 0:
                debug_print(f"COUNTER: {counter}, breaking", self.dlevel)
                break

        # if learned clause is unit, backtrack to 0 and propagate the literal
        # otherwise, backtrack to the 2nd highest decision level in the learnt clause (i.e. max dlevel of all literals excluding p_lit)
        out_btlevel = 0
        if len(out_learnt_lits) > 0:
            debug_print(f"Out_learnt_lits: {out_learnt_lits}", self.dlevel)
            for l in out_learnt_lits:
                v = abs(l)
                q_var_data = self.var_data[v]
                out_btlevel = max(out_btlevel, q_var_data.dlevel)
        
        out_learnt_lits.add(-p_lit)
        debug_print(f"Out_btlevel: {out_btlevel}, P_lit_dlevel: {self.var_data[abs(p_lit)].dlevel}, P_lit: {p_lit}", self.dlevel)
        if self.var_data[abs(p_lit)].dlevel > 0:
            assert self.var_data[abs(p_lit)].dlevel > out_btlevel
        
        debug_print(f"Out_btlevel: {out_btlevel}, Out_learnt_lits: {out_learnt_lits}", self.dlevel)
        
        return out_btlevel, out_learnt_lits, -p_lit

    def vsids(self) -> int:
        picked_lit = None
        while not picked_lit:
            lit, _ = self.activity.pop()
            if lit and abs(lit) not in self.assignments or self.value(lit) == 0:
                picked_lit = lit
        return picked_lit

    def branch_random_lit(self) -> int:
        for v in self.vars:
            if v not in self.assignments:
                debug_print(f"Branching on {v}", self.dlevel)
                return v
        assert False

    def solve(self) -> tuple[bool, dict[int, bool]]:
        print("============ SOLVING ============")
        while True:
            confl_cl = self.propagate()
            if confl_cl:
                if self.dlevel == 0:
                    return False, {}
                bt_level, learnt_lits, prop_lit = self.analyze(confl_cl)
                
                if len(learnt_lits) == 1:
                    assert bt_level == 0
                
                self.backtrackUntil(bt_level)
                new_clause = self.add_clause(clause=learnt_lits, learnt=True)
                if len(learnt_lits) > 1:
                    # Propagate the first UIP
                    # FIXME?: Should we assign one of the watched pointers in the new clause to the propagating literal?
                    
                    # TODO: Decay activity for var and clauses
                    assert new_clause
                    self.enqueue(prop_lit, new_clause)
                    
                # len(learnt_lits) == 1 => bt_level = 0; add_clause skips adding the clause and propagates directly

                self.activity.decay_scores()
                
            else:
                # TODO: Random restarts
                # TODO: Reduce # learned clauses

                if self.is_expression_sat():
                    return True, self.assignments
                
                if self.dlevel == 0 and not self.preprocess():
                    return False, self.assignments

                branchLit = self.vsids()
                # branchLit = self.branch_random_lit()
                self.dlevel += 1
                self.enqueue(branchLit)
    
    def is_expression_sat(self) -> bool:
        return len(self.assignments) == len(self.vars)

    def is_clause_sat(self, clause: Clause) -> bool:
        return any(self.value(l) == 1 for l in clause.lits)

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
        if self.clauses:
            for i, c in enumerate(self.clauses):
                result.append(f"Clause {i + 1}: {c.lits}")
        else:
            result.append("No clauses!")
        return "\n".join(result)



"""
2/19

BUG!

In C140.cnf, propagating on 2 should force -4 to propagate due to clause {-2, -4}. However, this doesn't happen. This implies that 2 is not watching clauses correctly


"""