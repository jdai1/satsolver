use std::fs::File;
use std::io::{BufRead, BufReader};
use crate::sat_instance::SatInstance;

pub struct DimacsParser {}

impl DimacsParser {
    pub fn parse_cnf_file(file_name: &str) -> Result<SatInstance, String> {

        let file: File = match File::open(file_name) {
            Ok(f) => f,
            Err(_) => return Err(format!("Error: DIMACS file is not found {}", file_name))
        };

        let reader: BufReader<File> = BufReader::new(file);
        let lines: Vec<String> = reader.lines().filter_map(Result::ok).collect();

        let mut start_index: usize= 0;
        let mut problem_line: Vec<&str> = Vec::new();
        
        for (i, line) in lines.iter().enumerate() {
            let tokens: Vec<&str> = line.trim().split_whitespace().collect();
            if tokens.is_empty() || tokens[0] == "c" {
                continue;
            }
            start_index = i + 1;
            problem_line = tokens;
            break;
        }

        if problem_line.is_empty() || problem_line[0] != "p" {
            return Err(format!("Error: DIMACS file does not have problem line"));
        }

        if problem_line[1] != "cnf" {
            return Err(format!("Error: DIMACS file format is not cnf"))
        }

        let num_vars = problem_line[2].parse::<u32>().unwrap();
        let num_clauses = problem_line[3].parse::<u32>().unwrap();
        let mut sat_instance: SatInstance = SatInstance::new(num_vars, num_clauses);

        let mut clause: Vec<i32> = Vec::new();
        for line in lines.iter().skip(start_index) {
            let tokens: Vec<&str> = line.trim().split_whitespace().collect();
            if tokens.is_empty() || tokens[0] == "c" {
                continue;
            }
            if *tokens.last().unwrap() != "0" {
                return Err(format!("Error: clause line does not end with 0: {:?}", {tokens}))
            }

            for &token in tokens.iter().take(tokens.len() - 1) {
                let lit = token.parse::<i32>().unwrap();
                sat_instance.add_var(lit);
                clause.push(lit);
            }

            sat_instance.add_clause(clause.clone());
            clause.clear();
        }

        Ok(sat_instance)
    }
}