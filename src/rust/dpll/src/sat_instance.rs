use std::collections::{HashMap, HashSet};
use std::mem;
use rand::Rng;

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
        }
    }
}

// DEBUGGING UTILS

#[derive(Debug)]
pub struct SatInstance {
    level: usize,
    num_vars: u32,
    num_clauses: u32,
    vars: HashSet<i32>,
    clauses: Vec<Clause>,
    active: HashSet<usize>, 
    unit_clauses: Vec<i32>,
    lit2clause: HashMap<i32, HashSet<usize>>,
    pub assignments: HashMap<i32, bool>,
}


impl SatInstance {
    pub fn new(num_vars: u32, num_clauses: u32) -> Self {
        SatInstance {
            level: 0,
            num_vars: num_vars,
            num_clauses: num_clauses,
            vars: HashSet::new(),
            clauses: Vec::new(),
            active: HashSet::new(),
            unit_clauses: Vec::new(),
            lit2clause: HashMap::new(),
            assignments: HashMap::new(),
        }
    }

    pub fn add_var(&mut self, lit: i32) {
        self.vars.insert(lit.abs());
    }

    pub fn add_clause(&mut self, lits: Vec<i32>) {
        if lits.len() == 1 {
            self.assign(lits[0]);
            return
        }
        let clause = Clause::new(lits);

        for l in clause.lits.iter() {
            if clause.lits.contains(&-(*l)) {
                return
            }
        }
        let cid = self.clauses.len();
        for l in clause.lits.iter() {
            self.lit2clause.entry(*l)
                .or_insert_with(HashSet::new)
                .insert(cid);
        }
        self.active.insert(cid);
        self.clauses.push(clause);
    }

    pub fn assign(&mut self, lit: i32) {
        self.unit_clauses.push(lit);
        self.assignments.insert(lit.abs(), lit > 0);
    }

    pub fn unit_propagate(&mut self) -> bool {
        while !self.unit_clauses.is_empty() {
            let p_lit = self.unit_clauses.pop().unwrap();
            // println!("{} Unit propagating {}", "--".repeat(self.level), p_lit);

            if let Some(clauses_ids) = self.lit2clause.get(&p_lit).cloned() {
                for cid in clauses_ids.iter() {
                    for l in self.clauses[*cid].lits.iter() {
                        if *l != p_lit {
                            if let Some(set) = self.lit2clause.get_mut(l) {
                                set.remove(cid);
                            }
                        }
                    }
                    // println!("{} Removing CID b/c clause contains unit clause: {}", "--".repeat(self.level), cid);
                    assert!(self.active.remove(cid));
                    
                }
            }

            self.lit2clause.remove(&p_lit);

            let not_p_lit = -p_lit;
            if let Some(clauses_ids) = self.lit2clause.get_mut(&not_p_lit).cloned() {
                for cid in clauses_ids.iter() {// let old_active_clauses = self.active;
                    let new_lits: Vec<i32> = self.clauses[*cid].lits.iter().filter(|&&l| l != not_p_lit).copied().collect();
                    if new_lits.is_empty() {
                        // println!("{} Conflict detected; empty clause", "--".repeat(self.level));
                        return true;
                    } else if new_lits.len() == 1 {
                        let new_p_lit = new_lits[0];
                        if let Some(&value) = self.assignments.get(&new_p_lit.abs()) {
                            if value != (new_p_lit > 0) {
                                // println!("{} Conflict detected: {}", "--".repeat(self.level), new_p_lit);
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

    pub fn ple(&mut self) {
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
                // println!("{} Calling PLE on {}", "--".repeat(self.level), pure_lit);
                self.assignments.insert(pure_lit.abs(), *pure_lit > 0);
                if let Some(clause_ids) = self.lit2clause.get(pure_lit).cloned() {
                    for cid in clause_ids.iter() {
                        for l in self.clauses[*cid].lits.iter() {
                            if let Some(set) = self.lit2clause.get_mut(l) {
                                set.remove(cid);
                            }
                        }
                        // println!("{} Removing CID: {}", "--".repeat(self.level), cid);
                        self.active.remove(cid);
                    }
                }
                self.lit2clause.remove(pure_lit);
            }
        }
    }

    pub fn dlis(&mut self) -> i32 {
        let mut max_count = 0;
        let mut max_lit = 0;
        for l in self.lit2clause.keys() {
            let count = self.lit2clause.get(l).unwrap().len();
            if count > max_count {
                max_count = count;
                max_lit = *l;
            }
        }
        // println!("{} DLIS Output: {}", "--".repeat(self.level), max_lit);
        max_lit
    }

    pub fn randomized_dlis(&mut self) -> i32 {
        let mut rng = rand::thread_rng();
        let mut top_lits = [(0, 0), (0, 0), (0, 0)]; // (lit, count)
        
        for l in self.lit2clause.keys() {
            let count = self.lit2clause.get(l).unwrap().len();
            for i in 0..3 {
                if count > top_lits[i].1 {
                    for j in (i+1..3).rev() {
                        top_lits[j] = top_lits[j-1];
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
        
        let selected_index = rng.gen_range(0..valid_count);
        // println!("{:?}", top_lits);
        // println!("{} Randomized DLIS Output: {}", "--".repeat(self.level), top_lits[selected_index].0);
        top_lits[selected_index].0
    }


    pub fn dlcs(&mut self) -> i32 {
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
        // println!("{} DLCS Output: {}", "--".repeat(self.level), max_lit);
        max_lit
    }

    pub fn randomized_dlcs(&mut self) -> i32 {
        let mut rng = rand::thread_rng();
        let mut top_lits = [(0, 0), (0, 0), (0, 0)]; // (lit, count)
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
                    for j in (i+1..3).rev() {
                        top_lits[j] = top_lits[j-1];
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
        let selected_index = rng.gen_range(0..valid_count);
        // println!("{:?}", top_lits);
        // println!("{} Randomized DLCS Output: {}", "--".repeat(self.level), top_lits[selected_index].0);
        top_lits[selected_index].0
    }

    pub fn copy_ds(&mut self) -> (HashMap<i32, bool>, HashMap<i32, HashSet<usize>>, Vec<i32>, HashSet<usize>, Vec<Clause>) {
        let mut new_assignments = HashMap::with_capacity(self.assignments.capacity());
        new_assignments.extend(self.assignments.iter().map(|(k, v)| (k.clone(), v.clone())));
        let old_assignments = mem::replace(&mut self.assignments, new_assignments);

        let mut new_lit2clause = HashMap::with_capacity(self.lit2clause.capacity());
        new_lit2clause.extend(self.lit2clause.iter().map(|(k, v)| (k.clone(), v.clone())));
        let old_lit2clause = mem::replace(&mut self.lit2clause, new_lit2clause);

        let mut new_unit_clauses = Vec::with_capacity(self.unit_clauses.capacity());
        new_unit_clauses.extend(self.unit_clauses.iter().cloned());
        let old_unit_clauses = mem::replace(&mut self.unit_clauses, new_unit_clauses);

        let mut new_active_clauses = HashSet::with_capacity(self.active.capacity());
        new_active_clauses.extend(self.active.iter().cloned());
        let old_active_clauses = mem::replace(&mut self.active, new_active_clauses);

        let mut new_clauses = Vec::with_capacity(self.clauses.capacity());
        new_clauses.extend(self.clauses.iter().cloned());
        let old_clauses = mem::replace(&mut self.clauses, new_clauses);

        return (old_assignments, old_lit2clause, old_unit_clauses, old_active_clauses, old_clauses);
    }

    pub fn solve(&mut self) -> bool {
        if self.unit_propagate() {
            return false;
        }
        self.ple();

        if self.active.is_empty() {
            return true;
        }
        
        let p_lit = self.dlis();
        let (old_assignments, old_lit2clause, old_unit_clauses, old_active_clauses, old_clauses) = self.copy_ds();

        self.assign(p_lit);
        self.level += 1;
        // println!("{} Branching on {}", "--".repeat(self.level), p_lit);

        let branch_a = self.solve();
        if branch_a {
            return branch_a;
        }

        self.assignments = old_assignments;
        self.lit2clause = old_lit2clause;
        self.unit_clauses = old_unit_clauses;
        self.active = old_active_clauses;
        self.clauses = old_clauses;

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

    pub fn value(&mut self, lit: i32) -> bool {
        if let Some(&value) = self.assignments.get(&lit.abs()) {
            if lit > 0 {
                return value;
            }
            return !value;
        }
        false
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