use rand::Rng;
use std::collections::{HashMap, HashSet};
use std::mem;

macro_rules! l_index {
    ($l:expr, $num_vars:expr) => {
        if $l > 0 {
            ($l - 1) as usize
        } else {
            ($l.abs() + $num_vars - 1) as usize
        }
    };
}

macro_rules! v_index {
    ($l:expr) => {
        ($l.abs() - 1) as usize
    };
}

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

#[derive(Debug)]
pub struct SatInstance {
    level: i32,
    var_id: usize,
    clause_id: usize,
    num_vars: i32,
    num_clauses: i32,
    ref_count: i32,
    var_map: HashMap<i32, i32>,
    reverse_var_map: HashMap<i32, i32>,
    assignments: Vec<i32>,
    clauses: Vec<Clause>,
    unit_literals: Vec<i32>,
    lit2clause: Vec<HashSet<i32>>,
}

impl SatInstance {
    pub fn new(num_vars: i32, num_clauses: i32) -> Self {
        SatInstance {
            level: 0,
            var_id: 1,
            clause_id: 1,
            num_vars: num_vars,
            num_clauses: num_clauses,
            ref_count: 0,
            var_map: HashMap::new(),
            reverse_var_map: HashMap::new(),
            assignments: vec![0; num_vars.try_into().unwrap()],
            clauses: vec![Clause::new(Vec::new()); num_clauses.try_into().unwrap()],
            unit_literals: Vec::new(),
            lit2clause: vec![HashSet::new(); (num_vars * 2).try_into().unwrap()], // add two entries in lit2clause per variable (for positive and negative occurence)
        }
    }

    pub fn add_var(&mut self, lit: i32) {
        let v = lit.abs();
        if !self.var_map.contains_key(&v) {
            // maintain mapping in both directions
            self.var_map.insert(v, self.var_id as i32);
            self.reverse_var_map.insert(self.var_id as i32, v);
            self.var_id += 1;
        }
    }

    // NOTE: All variables are added; then all clauses are added
    pub fn add_clause(&mut self, lits: Vec<i32>) {
        let mut new_lits = Vec::new();
        for &l in lits.iter() {
            let new_var = *self.var_map.get(&l.abs()).unwrap();
            let new_lit = if l > 0 { new_var } else { -new_var };
            new_lits.push(new_lit);
        }
        if new_lits.len() == 1 {
            self.assign(new_lits[0]);
            return;
        }

        // checking for tautologies
        for l in new_lits.iter() {
            if new_lits.contains(&-(*l)) {
                return;
            }
        }
        for l in new_lits.iter() {
            let l_idx = l_index!(*l, self.num_vars);
            
            if !self.lit2clause[l_idx].contains(&(self.clause_id as i32)) {
                self.ref_count += 1;
                self.lit2clause[l_idx].insert(self.clause_id as i32);
            }
        }

        self.clauses[self.clause_id - 1].lits.extend(new_lits);
        self.clause_id += 1;
    }

    pub fn assign(&mut self, lit: i32) {
        let idx = v_index!(lit);
        if self.assignments[idx] == 0 {
            self.unit_literals.push(lit);
            self.assignments[idx] = if lit > 0 { 1 } else { -1 };
        }
    }

    pub fn unit_propagate(&mut self) -> bool {
        while !self.unit_literals.is_empty() {
            let p_lit = self.unit_literals.pop().unwrap();
            let p_lit_idx = l_index!(p_lit, self.num_vars);
            // println!(
            //     "{} Unit propagating {}",
            //     "--".repeat(self.level as usize),
            //     p_lit
            // );

            let cids: Vec<i32> = self.lit2clause[p_lit_idx].iter().cloned().collect();
            for cid in cids {
                for &l in self.clauses[(cid - 1) as usize].lits.iter() {
                    if l != p_lit {
                        if self.lit2clause[l_index!(l, self.num_vars)].remove(&cid) {
                            self.ref_count -= 1;
                        }
                    }
                }
            }
            self.ref_count -= self.lit2clause[p_lit_idx].len() as i32;
            self.lit2clause[p_lit_idx].clear();
            assert!(self.lit2clause[p_lit_idx].is_empty());

            let not_p_lit = -p_lit;
            let not_p_lit_idx = l_index!(not_p_lit, self.num_vars);
            let not_p_cids: Vec<i32> = self.lit2clause[not_p_lit_idx].iter().cloned().collect();
            for cid in not_p_cids {
                // let old_active_clauses = self.active;

                // TODO: Implement watched literals
                let new_lits: Vec<i32> = self.clauses[(cid - 1) as usize]
                    .lits
                    .iter()
                    .filter(|&&l| l != not_p_lit)
                    .copied()
                    .collect();

                if new_lits.is_empty() {
                    return true;
                } else if new_lits.len() == 1 {
                    let new_p_lit = new_lits[0];
                    let assgn_idx: usize = v_index!(new_p_lit);
                    if (self.assignments[assgn_idx] == 1 && new_p_lit < 0)
                        || (self.assignments[assgn_idx] == -1 && new_p_lit > 0)
                    {
                        return true;
                    }
                    self.assign(new_p_lit);
                    self.ref_count -= 1;
                    assert!(self.lit2clause[not_p_lit_idx].remove(&cid));
                } else {
                    self.clauses[(cid - 1) as usize].lits = new_lits;
                }
            }
            self.ref_count -= self.lit2clause[not_p_lit_idx].len() as i32;
            self.lit2clause[not_p_lit_idx].clear();
            assert!(self.lit2clause[not_p_lit_idx].is_empty());
        }
        false
    }

    pub fn ple(&mut self) {
        loop {
            let mut pure_literals: Vec<i32> = Vec::new();
            let mut var = 0;
            let mut pos_count = 0;
            let mut neg_count = 0;
            for (i, &value) in self.assignments.iter().enumerate() {
                // skip if variable has already been assigned
                if value != 0 {
                    continue;
                }

                var = i + 1;
                pos_count = self.lit2clause[l_index!(var as i32, self.num_vars)].len();
                neg_count = self.lit2clause[l_index!(-(var as i32), self.num_vars)].len();
                if pos_count > 0 && neg_count == 0 {
                    pure_literals.push(var as i32);
                } else if pos_count == 0 && neg_count > 0 {
                    pure_literals.push(-(var as i32));
                }
            }

            if pure_literals.is_empty() {
                break;
            }

            let mut pure_lit_idx = 0;
            let mut cids: Vec<i32>;
            for &pure_lit in pure_literals.iter() {
                // println!(
                //     "{} Calling PLE on {}",
                //     "--".repeat(self.level as usize),
                //     pure_lit
                // );
                pure_lit_idx = l_index!(pure_lit, self.num_vars);
                self.assignments[v_index!(pure_lit)] = if pure_lit > 0 { 1 } else { -1 };
                cids = self.lit2clause[pure_lit_idx].iter().cloned().collect();
                for &cid in cids.iter() {
                    for &l in self.clauses[(cid - 1) as usize].lits.iter() {
                        
                        if self.lit2clause[l_index!(l, self.num_vars)].remove(&cid) {
                            self.ref_count -= 1;
                        }
                    }
                }
                self.ref_count -= self.lit2clause[pure_lit_idx].len() as i32;
                self.lit2clause[pure_lit_idx].clear();
                cids.clear();
            }
        }
    }

    pub fn dlis(&mut self) -> i32 {
        let mut max_lit: i32 = 0;
        let mut max_count: usize = 0;
        let mut var: usize = 0;
        let mut pos_count: usize = 0;
        let mut neg_count: usize = 0;
        for (i, &value) in self.assignments.iter().enumerate() {
            // skip if variable has already been assigned
            if value != 0 {
                continue;
            }
            var = i + 1;
            
            pos_count = self.lit2clause[l_index!(var as i32, self.num_vars)].len();
            neg_count = self.lit2clause[l_index!(-(var as i32), self.num_vars)].len();
            if pos_count > max_count {
                max_count = pos_count;
                max_lit = var as i32;
            }
            if neg_count > max_count {
                max_count = neg_count;
                max_lit = -(var as i32)
            }
        }
        max_lit
    }

    // pub fn randomized_dlis(&mut self) -> i32 {
    //     let mut rng = rand::rng();
    //     let mut top_lits = [(0, 0), (0, 0), (0, 0)]; // (lit, count)

    //     for l in self.lit2clause.keys() {
    //         let count = self.lit2clause.get(l).unwrap().len();
    //         for i in 0..3 {
    //             if count > top_lits[i].1 {
    //                 for j in (i+1..3).rev() {
    //                     top_lits[j] = top_lits[j-1];
    //                 }
    //                 top_lits[i] = (*l, count);
    //                 break;
    //             }
    //         }
    //     }
    //     let mut valid_count = 0;
    //     for i in 0..3 {
    //         if top_lits[i].0 != 0 {
    //             valid_count += 1;
    //         }
    //     }
    //     assert!(valid_count > 0);

    //     let selected_index = rng.random_range(0..valid_count);
    //     // println!("{:?}", top_lits);
    //     // println!("{} Randomized DLIS Output: {}", "--".repeat(self.level), top_lits[selected_index].0);
    //     top_lits[selected_index].0
    // }

    // pub fn dlcs(&mut self) -> i32 {
    //     let mut max_count = 0;
    //     let mut max_lit = 0;
    //     let mut pos_count = 0;
    //     let mut neg_count = 0;
    //     for v in self.vars.iter() {
    //         pos_count = if let Some(set) = self.lit2clause.get(v) {
    //             set.len()
    //         } else {
    //             0
    //         };
    //         neg_count = if let Some(set) = self.lit2clause.get(&-(*v)) {
    //             set.len()
    //         } else {
    //             0
    //         };
    //         if pos_count + neg_count > max_count {
    //             max_count = pos_count + neg_count;
    //             max_lit = if pos_count > neg_count { *v } else { -(*v) };
    //         }
    //     }
    //     // println!("{} DLCS Output: {}", "--".repeat(self.level), max_lit);
    //     max_lit
    // }

    // pub fn randomized_dlcs(&mut self) -> i32 {
    //     let mut rng = rand::rng();
    //     let mut top_lits = [(0, 0), (0, 0), (0, 0)]; // (lit, count)
    //     let mut pos_count = 0;
    //     let mut neg_count = 0;
    //     for v in self.vars.iter() {
    //         pos_count = if let Some(set) = self.lit2clause.get(v) {
    //             set.len()
    //         } else {
    //             0
    //         };
    //         neg_count = if let Some(set) = self.lit2clause.get(&-(*v)) {
    //             set.len()
    //         } else {
    //             0
    //         };

    //         let combined_count = pos_count + neg_count;
    //         for i in 0..3 {
    //             if combined_count > top_lits[i].1 {
    //                 for j in (i+1..3).rev() {
    //                     top_lits[j] = top_lits[j-1];
    //                 }
    //                 let p_lit = if pos_count > neg_count { *v } else { -(*v) };
    //                 top_lits[i] = (p_lit, combined_count);
    //                 break;
    //             }
    //         }
    //     }
    //     let mut valid_count = 0;
    //     for i in 0..3 {
    //         if top_lits[i].0 != 0 {
    //             valid_count += 1;
    //         }
    //     }
    //     assert!(valid_count > 0);
    //     let selected_index = rng.random_range(0..valid_count);
    //     // println!("{:?}", top_lits);
    //     // println!("{} Randomized DLCS Output: {}", "--".repeat(self.level), top_lits[selected_index].0);
    //     top_lits[selected_index].0
    // }

    pub fn copy_ds(&mut self) -> (Vec<i32>, Vec<HashSet<i32>>, Vec<Clause>) {
        let mut new_assignments = Vec::with_capacity(self.assignments.capacity());
        new_assignments.extend(self.assignments.iter().cloned());
        let old_assignments = mem::replace(&mut self.assignments, new_assignments);

        let mut new_lit2clause: Vec<HashSet<i32>> = Vec::with_capacity(self.lit2clause.capacity());
        new_lit2clause.extend(self.lit2clause.iter().cloned());
        let old_lit2clause = mem::replace(&mut self.lit2clause, new_lit2clause);

        let mut new_clauses = Vec::with_capacity(self.clauses.capacity());
        new_clauses.extend(self.clauses.iter().cloned());
        let old_clauses = mem::replace(&mut self.clauses, new_clauses);

        return (old_assignments, old_lit2clause, old_clauses);
    }

    pub fn solve(&mut self) -> bool {
        if self.unit_propagate() {
            return false;
        }
        self.ple();

        if self.ref_count == 0 {
            return true;
        }

        let p_lit = self.dlis();

        let old_ref_count = self.ref_count;
        let (old_assignments, old_lit2clause, old_clauses) = self.copy_ds();
        self.assign(p_lit);
        
        // println!(
        //     "{} Branching on {}",
        //     "--".repeat(self.level as usize),
        //     p_lit
        // );

        self.level += 1;

        let branch_a = self.solve();
        if branch_a {
            return branch_a;
        }
        self.level -= 1;
        self.assignments = old_assignments;
        self.lit2clause = old_lit2clause;
        self.clauses = old_clauses;
        self.ref_count = old_ref_count;
        self.unit_literals.clear();

        // println!(
        //     "{} Branching on {}",
        //     "--".repeat(self.level as usize),
        //     -p_lit
        // );

        self.assign(-p_lit);
        return self.solve();
    }

    pub fn check(&mut self) -> bool {
        let clauses = &self.clauses.clone();
        for c in clauses.iter() {
            if c.lits.is_empty() {
                continue
            }
            if !c.lits.iter().any(|&l| {
                if l > 0 {
                    self.assignments[v_index!(l)] == 1
                } else {
                    self.assignments[v_index!(l)] == -1
                }
            }) {
                println!("{:?} wasn't satisfied", c.lits);
                return false;
            }
        }
        true
    }

    pub fn to_string(&self) -> String {
        let mut result = Vec::new();

        result.push(format!("Number of variables: {}", self.num_vars));
        result.push(format!("Number of clauses: {}", self.num_clauses));
        result.push(format!("Var ID: {}", self.var_id));
        result.push(format!("Clause ID: {}", self.clause_id));
        result.push(format!("Variables: {:?}", self.var_map));

        if !self.clauses.is_empty() {
            for (i, clause) in self.clauses.iter().enumerate() {
                result.push(format!("Clause {}: {:?}", i + 1, clause.lits));
            }
        } else {
            result.push("No clauses!".to_string());
        }

        result.join("\n")
    }

    pub fn get_assignment_string(&self) -> String {
        let mut assignment_str = String::new();
        for i in 1..self.var_id {
            let value = self.assignments[i - 1];
            assignment_str.push_str(&format!(
                "{} {} ",
                self.reverse_var_map[&(i as i32)],
                if value == 1 { "True" } else { "False" }
            ));
        }
        if assignment_str.ends_with(' ') {
            assignment_str = assignment_str.trim_end().to_string();
        }
        assignment_str
    }
}
