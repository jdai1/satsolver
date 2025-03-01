mod clock;
mod dimacs_parser;
mod sat_instance;

use clock::Clock;
use core_affinity::CoreId;
use sat_instance::{SatInstance, SearchHeuristic};
use std::cmp::max;
use std::env;
use std::path::Path;
use std::sync::mpsc;
use std::thread;

use crate::dimacs_parser::DimacsParser;

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        println!("Usage: python main.py <cnf file>");
        return;
    }

    let (sender, receiver) = mpsc::channel();
    let cores: Vec<CoreId> = core_affinity::get_core_ids().unwrap();
    let core_count = cores.len();

    for i in 0..5{
        let sender = sender.clone();
        let core_id = cores[i % core_count]; // Distribute threads across cores
        let args = args.clone();
        let heuristics = vec![SearchHeuristic::DLIS, SearchHeuristic::DLCS, SearchHeuristic::RandDLCS, SearchHeuristic::RandDLIS, SearchHeuristic::Hybrid];
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

            sat_instance.set_heuristic(heuristics[i].clone());

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
            sender.send((sat, sat_instance.assignments, watch.get_time())).unwrap();
        });
    }

    drop(sender);
    // let mut unsat_time = 0.0;
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
        } else {
            println!(
                "{{\"Instance\": \"{}\", \"Time\": \"{:.2}\", \"Result\": \"{}\"}}",
                args[1],
                time,
                "UNSAT"
            );
        }
        return;
        // unsat_time = time.max(unsat_time);
    }

    
}
