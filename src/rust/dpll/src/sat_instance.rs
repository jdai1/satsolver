use fxhash::{FxHashMap, FxHashSet};
use rand::Rng;
use std::collections::{HashMap, HashSet};
use std::mem;

#[derive(Debug, PartialEq, Eq, Hash, Clone)]
pub struct Clause {
    pub lits: Vec<i32>,
    pub size: usize,
}

impl Clause {
    pub fn new(lits: Vec<i32>) -> Self {
        return Clause {
            size: lits.len(),
            lits: lits,
        };
    }
}

#[derive(Debug, Copy, Clone)]
pub enum SearchHeuristic {
    DLIS,
    DLCS,
    RandDLIS,
    RandDLCS,
    Hybrid,
}

#[derive(Debug)]
pub struct SatInstance {
    search_heuristic: SearchHeuristic,
    level: usize,
    num_vars: u32,
    num_clauses: u32,
    vars: FxHashSet<i32>,
    clauses: Vec<Clause>,
    active: FxHashSet<usize>,
    unit_clauses: Vec<i32>,
    lit2clause: FxHashMap<i32, FxHashSet<usize>>,
    pub assignments: FxHashMap<i32, bool>,
}

impl SatInstance {
    pub fn new(num_vars: u32, num_clauses: u32) -> Self {
        SatInstance {
            search_heuristic: SearchHeuristic::DLIS,
            level: 0,
            num_vars: num_vars,
            num_clauses: num_clauses,
            vars: FxHashSet::default(),
            clauses: Vec::new(),
            active: FxHashSet::default(),
            unit_clauses: Vec::new(),
            lit2clause: FxHashMap::default(),
            assignments: FxHashMap::default(),
        }
    }

    pub fn add_var(&mut self, lit: i32) {
        self.vars.insert(lit.abs());
    }

    pub fn add_clause(&mut self, lits: Vec<i32>) {
        if lits.len() == 1 {
            self.assign(lits[0]);
            return;
        }
        let clause = Clause::new(lits);

        for l in clause.lits.iter() {
            if clause.lits.contains(&-(*l)) {
                return;
            }
        }
        let cid = self.clauses.len();
        for l in clause.lits.iter() {
            self.lit2clause
                .entry(*l)
                .or_insert_with(FxHashSet::default)
                .insert(cid);
        }
        self.active.insert(cid);
        self.clauses.push(clause);
    }

    pub fn set_heuristic(&mut self, heuristic: SearchHeuristic) {
        self.search_heuristic = heuristic;
    }

    pub fn assign(&mut self, lit: i32) {
        self.unit_clauses.push(lit);
        self.assignments.insert(lit.abs(), lit > 0);
    }

    fn value(&mut self, lit: i32) -> bool {
        if let Some(&value) = self.assignments.get(&lit.abs()) {
            if lit > 0 {
                return value;
            }
            return !value;
        }
        false
    }

    fn unit_propagate(&mut self) -> bool {
        while !self.unit_clauses.is_empty() {
            let p_lit = self.unit_clauses.pop().unwrap();
            if let Some(clauses_ids) = self.lit2clause.get(&p_lit).cloned() {
                for cid in clauses_ids.iter() {
                    for l in self.clauses[*cid].lits.iter() {
                        if *l != p_lit {
                            if let Some(set) = self.lit2clause.get_mut(l) {
                                set.remove(cid);
                            }
                        }
                    }
                    assert!(self.active.remove(cid));
                }
            }

            self.lit2clause.remove(&p_lit);

            let not_p_lit = -p_lit;
            if let Some(clauses_ids) = self.lit2clause.get_mut(&not_p_lit).cloned() {
                for cid in clauses_ids.iter() {
                    // let old_active_clauses = self.active;
                    let new_lits: Vec<i32> = self.clauses[*cid]
                        .lits
                        .iter()
                        .filter(|&&l| l != not_p_lit)
                        .copied()
                        .collect();
                    if new_lits.is_empty() {
                        return true;
                    } else if new_lits.len() == 1 {
                        let new_p_lit = new_lits[0];
                        if let Some(&value) = self.assignments.get(&new_p_lit.abs()) {
                            if value != (new_p_lit > 0) {
                                return true;
                            }
                        }
                        self.assign(new_p_lit);
                        self.active.remove(cid);
                        self.lit2clause.get_mut(&new_p_lit).unwrap().remove(cid);
                    } else {
                        self.clauses[*cid].lits = new_lits;
                    }
                }
                self.lit2clause.remove(&not_p_lit);
            }
        }
        false
    }

    fn ple(&mut self) {
        loop {
            let mut pure_literals: Vec<i32> = Vec::new();
            for l in self.lit2clause.keys() {
                if !self.lit2clause.contains_key(&-(*l)) {
                    pure_literals.push(*l);
                }
            }
            if pure_literals.is_empty() {
                return;
            }

            for pure_lit in pure_literals.iter() {
                self.assignments.insert(pure_lit.abs(), *pure_lit > 0);
                if let Some(clause_ids) = self.lit2clause.get(pure_lit).cloned() {
                    for cid in clause_ids.iter() {
                        for l in self.clauses[*cid].lits.iter() {
                            if let Some(set) = self.lit2clause.get_mut(l) {
                                set.remove(cid);
                            }
                        }
                        self.active.remove(cid);
                    }
                }
                self.lit2clause.remove(pure_lit);
            }
        }
    }

    // Search heuristics

    fn dlis(&mut self) -> i32 {
        let mut max_count = 0;
        let mut max_lit = 0;
        for l in self.lit2clause.keys() {
            let count = self.lit2clause.get(l).unwrap().len();
            if count > max_count {
                max_count = count;
                max_lit = *l;
            }
        }
        max_lit
    }

    pub fn randomized_dlis(&mut self) -> ([(i32, usize); 3], usize) {
        let mut rng = rand::rng();
        let mut top_lits: [(i32, usize); 3] = [(0, 0), (0, 0), (0, 0)]; // (lit, count)

        for l in self.lit2clause.keys() {
            let count = self.lit2clause.get(l).unwrap().len();
            for i in 0..3 {
                if count > top_lits[i].1 {
                    for j in (i + 1..3).rev() {
                        top_lits[j] = top_lits[j - 1];
                    }
                    top_lits[i] = (*l, count);
                    break;
                }
            }
        }
        let mut valid_count = 0;
        for i in 0..3 {
            if top_lits[i].0 != 0 {
                valid_count += 1;
            }
        }
        assert!(valid_count > 0);
        (top_lits, rng.random_range(0..valid_count))
    }

    fn dlcs(&mut self) -> i32 {
        let mut max_count = 0;
        let mut max_lit = 0;
        let mut pos_count = 0;
        let mut neg_count = 0;
        for v in self.vars.iter() {
            pos_count = if let Some(set) = self.lit2clause.get(v) {
                set.len()
            } else {
                0
            };
            neg_count = if let Some(set) = self.lit2clause.get(&-(*v)) {
                set.len()
            } else {
                0
            };
            if pos_count + neg_count > max_count {
                max_count = pos_count + neg_count;
                max_lit = if pos_count > neg_count { *v } else { -(*v) };
            }
        }
        max_lit
    }

    pub fn randomized_dlcs(&mut self) -> ([(i32, usize); 3], usize) {
        let mut rng = rand::rng();
        let mut top_lits: [(i32, usize); 3] = [(0, 0), (0, 0), (0, 0)]; // (lit, count)
        let mut pos_count = 0;
        let mut neg_count = 0;
        for v in self.vars.iter() {
            pos_count = if let Some(set) = self.lit2clause.get(v) {
                set.len()
            } else {
                0
            };
            neg_count = if let Some(set) = self.lit2clause.get(&-(*v)) {
                set.len()
            } else {
                0
            };

            let combined_count = pos_count + neg_count;
            for i in 0..3 {
                if combined_count > top_lits[i].1 {
                    for j in (i + 1..3).rev() {
                        top_lits[j] = top_lits[j - 1];
                    }
                    let p_lit = if pos_count > neg_count { *v } else { -(*v) };
                    top_lits[i] = (p_lit, combined_count);
                    break;
                }
            }
        }
        let mut valid_count = 0;
        for i in 0..3 {
            if top_lits[i].0 != 0 {
                valid_count += 1;
            }
        }
        assert!(valid_count > 0);
        (top_lits, rng.random_range(0..valid_count))
    }

    pub fn get_branch_lit(&mut self) -> i32 {
        match self.search_heuristic {
            SearchHeuristic::DLCS => self.dlcs(),
            SearchHeuristic::DLIS => self.dlis(),
            SearchHeuristic::RandDLCS => {
                let (top_lits, selected_index) = self.randomized_dlcs();
                top_lits[selected_index].0
            }
            SearchHeuristic::RandDLIS => {
                let (top_lits, selected_index) = self.randomized_dlis();
                top_lits[selected_index].0
            }
            SearchHeuristic::Hybrid => {
                if rand::random_bool(0.5) {
                    self.dlcs()
                } else {
                    self.dlis()
                }
            }
        }
    }

    fn copy_ds(
        &mut self,
    ) -> (
        FxHashMap<i32, bool>,
        FxHashMap<i32, FxHashSet<usize>>,
        FxHashSet<usize>,
        Vec<Clause>,
    ) {
        let mut new_assignments =
            FxHashMap::with_capacity_and_hasher(self.assignments.capacity(), Default::default());
        new_assignments.extend(self.assignments.iter().map(|(k, v)| (k.clone(), v.clone())));
        let old_assignments = mem::replace(&mut self.assignments, new_assignments);

        let mut new_lit2clause =
            FxHashMap::with_capacity_and_hasher(self.lit2clause.capacity(), Default::default());
        new_lit2clause.extend(self.lit2clause.iter().map(|(k, v)| (k.clone(), v.clone())));
        let old_lit2clause = mem::replace(&mut self.lit2clause, new_lit2clause);

        let mut new_active_clauses =
            FxHashSet::with_capacity_and_hasher(self.active.capacity(), Default::default());
        new_active_clauses.extend(self.active.iter().cloned());
        let old_active_clauses = mem::replace(&mut self.active, new_active_clauses);

        let mut new_clauses = Vec::with_capacity(self.clauses.capacity());
        new_clauses.extend(self.clauses.iter().cloned());
        let old_clauses = mem::replace(&mut self.clauses, new_clauses);

        return (
            old_assignments,
            old_lit2clause,
            old_active_clauses,
            old_clauses,
        );
    }

    pub fn solve(&mut self) -> bool {
        if self.unit_propagate() {
            return false;
        }
        self.ple();

        if self.active.is_empty() {
            return true;
        }

        let p_lit = self.get_branch_lit();

        let (old_assignments, old_lit2clause, old_active_clauses, old_clauses) = self.copy_ds();

        self.assign(p_lit);
        self.level += 1;
        // println!("{} Branching on {}", "--".repeat(self.level), p_lit);

        let branch_a = self.solve();
        if branch_a {
            return branch_a;
        }

        self.assignments = old_assignments;
        self.lit2clause = old_lit2clause;
        self.active = old_active_clauses;
        self.clauses = old_clauses;
        self.unit_clauses.clear();

        // println!("{} Branching on {}", "--".repeat(self.level), -p_lit);

        self.assign(-p_lit);
        return self.solve();
    }

    pub fn check(&mut self) -> bool {
        let clauses = &self.clauses.clone();
        for c in clauses.iter() {
            if !c.lits.iter().any(|x| self.value(*x)) {
                return false;
            }
        }
        true
    }

    pub fn to_string(&self) -> String {
        let mut result = Vec::new();

        result.push(format!("Number of variables: {}", self.num_vars));
        result.push(format!("Number of clauses: {}", self.num_clauses));
        result.push(format!("Variables: {:?}", self.vars));

        if !self.clauses.is_empty() {
            for (i, clause) in self.clauses.iter().enumerate() {
                result.push(format!("Clause {}: {:?}", i + 1, clause.lits));
            }
        } else {
            result.push("No clauses!".to_string());
        }

        result.join("\n")
    }
}
