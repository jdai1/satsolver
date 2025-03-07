mod clock;
mod dimacs_parser;
mod sat_instance;

use clock::Clock;
use sat_instance::SatInstance;
use std::env;
use std::path::Path;
use tokio::time::{timeout, Duration};

use crate::dimacs_parser::DimacsParser;

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        println!("Usage: python main.py <cnf file>");
        return;
    }
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
    println!(
        "{{\"Instance\": \"{}\", \"Time\": {:.2}, \"Result\": \"--\"}}",
        filename,
        watch.get_time()
    );

    // println!("{}", sat_instance.to_string());

    watch.start();
    let sat = sat_instance.solve();
    watch.stop();
    if sat {
        let assignment_str = sat_instance.get_assignment_string();
        println!("Correct: {:?}", sat_instance.check());
        println!(
            "{{\"Instance\": \"{}\", \"Time\": \"{:.2}\", \"Result\": \"{}\", \"Solution\": \"{}\"}}",
            filename,
            watch.get_time(),
            "SAT",
            assignment_str
        );
    } else {
        println!(
            "{{\"Instance\": \"{}\", \"Time\": \"{:.2}\", \"Result\": \"{}\"}}",
            filename,
            watch.get_time(),
            "UNSAT"
        );
    }
}
