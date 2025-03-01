mod clock;
mod dimacs_parser;
mod sat_instance;

use clock::Clock;
use core_affinity::CoreId;
use sat_instance::{SatInstance, SearchHeuristic};
use std::env;
use std::path::Path;
use std::sync::mpsc;
use std::thread;

use crate::dimacs_parser::DimacsParser;

fn run_parallel_heuristics(args: Vec<String>) {
    let (sender, receiver) = mpsc::channel();
    let cores: Vec<CoreId> = core_affinity::get_core_ids().unwrap();
    let core_count = cores.len();

    for i in 0..8 {
        let sender = sender.clone();
        let core_id = cores[i % core_count]; // Distribute threads across cores
        let args = args.clone();
        let heuristics = vec![
            SearchHeuristic::DLIS,
            SearchHeuristic::DLCS,
            SearchHeuristic::RandDLCS,
            SearchHeuristic::RandDLIS,
            SearchHeuristic::Hybrid,
            SearchHeuristic::RandDLIS,
            SearchHeuristic::RandDLIS,
            SearchHeuristic::RandDLIS,
        ];
        thread::spawn(move || {
            core_affinity::set_for_current(core_id);

            let input_file = args[1].clone();
            let filename = Path::new(input_file.as_str())
                .file_name()
                .unwrap()
                .to_str()
                .unwrap();

            let mut watch = Clock::new();
            watch.start();
            let mut sat_instance: SatInstance = DimacsParser::parse_cnf_file(&input_file).unwrap();
            watch.stop();

            sat_instance.set_heuristic(heuristics[i]);

            println!(
                "{{\"Instance\": \"{}\", \"Time\": {:.2}, \"Result\": \"--\"}}",
                filename,
                watch.get_time()
            );

            watch.start();
            let sat = sat_instance.solve();
            watch.stop();

            if sat {
                assert!(sat_instance.check());
            }
            sender
                .send((
                    sat,
                    sat_instance.assignments,
                    watch.get_time(),
                    heuristics[i],
                ))
                .unwrap();
        });
    }

    drop(sender);
    for (sat, assignments, time, heuristic) in receiver {
        if sat {
            let mut assignment_str = String::new();
            for (var, value) in assignments {
                assignment_str.push_str(&format!(
                    "{} {} ",
                    var,
                    if value { "true" } else { "false" }
                ));
            }
            if assignment_str.ends_with(' ') {
                assignment_str = assignment_str.trim_end().to_string();
            }
            println!(
                "{{\"Instance\": \"{}\", \"Time\": \"{:.2}\", \"Result\": \"{}\", \"Solution\": \"{}\"}}",
                args[1],
                time,
                "SAT",
                assignment_str
            );
            return;
        } else {
            println!(
                "{{\"Instance\": \"{}\", \"Time\": \"{:.2}\", \"Result\": \"{}\"}}",
                args[1], time, "UNSAT"
            );
        }
        return;
    }
}

fn run_parallel_assignments(args: Vec<String>) {
    let (sender, receiver) = mpsc::channel();
    let cores: Vec<CoreId> = core_affinity::get_core_ids().unwrap();
    let core_count = cores.len();

    let input_file = args[1].clone();
    let mut sat_instance: SatInstance = DimacsParser::parse_cnf_file(&input_file).unwrap();

    let (top_lits, _) = sat_instance.randomized_dlcs();
    let first_lit = top_lits[0].0;
    let second_lit = top_lits[1].0;
    let third_lit = top_lits[2].0;
    let truth_assignments = [
        [true, true, true],
        [true, true, false],
        [true, false, true],
        [true, false, false],
        [false, true, true],
        [false, true, false],
        [false, false, true],
        [false, false, false],
    ];

    for i in 0..8 {
        let sender = sender.clone();
        let core_id = cores[i % core_count]; // Distribute threads across cores
        let args = args.clone();
        thread::spawn(move || {
            core_affinity::set_for_current(core_id);

            let input_file = args[1].clone();
            let mut watch = Clock::new();
            watch.start();
            let mut sat_instance: SatInstance = DimacsParser::parse_cnf_file(&input_file).unwrap();
            watch.stop();

            sat_instance.set_heuristic(SearchHeuristic::RandDLIS);

            sat_instance.assign(if truth_assignments[i][0] {first_lit} else {-first_lit});
            sat_instance.assign(if truth_assignments[i][1] {second_lit} else {-second_lit});
            sat_instance.assign(if truth_assignments[i][2] {third_lit} else {-third_lit});

            watch.start();
            let sat = sat_instance.solve();
            watch.stop();

            if sat {
                assert!(sat_instance.check());
            }
            sender
                .send((sat, sat_instance.assignments, watch.get_time()))
                .unwrap();
        });
    }

    drop(sender);
    let mut unsat_time = 0.0;
    for (sat, assignments, time) in receiver {
        if sat {
            let mut assignment_str = String::new();
            for (var, value) in assignments {
                assignment_str.push_str(&format!(
                    "{} {} ",
                    var,
                    if value { "true" } else { "false" }
                ));
            }
            if assignment_str.ends_with(' ') {
                assignment_str = assignment_str.trim_end().to_string();
            }
            println!(
                "{{\"Instance\": \"{}\", \"Time\": \"{:.2}\", \"Result\": \"{}\", \"Solution\": \"{}\"}}",
                args[1],
                time,
                "SAT",
                assignment_str
            );
            return;
        }
        unsat_time = time.max(unsat_time);
    }
    println!(
        "{{\"Instance\": \"{}\", \"Time\": \"{:.2}\", \"Result\": \"{}\"}}",
        args[1], unsat_time, "UNSAT"
    );
    
}

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        println!("Usage: python main.py <cnf file>");
        return;
    }

    // run_parallel_heuristics(args.clone());
    run_parallel_assignments(args.clone());
}
