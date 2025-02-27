mod clock;
mod dimacs_parser;
mod sat_instance;

use clock::Clock;
use sat_instance::SatInstance;
use std::env;
use std::path::Path;

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

    watch.start();
    let sat = sat_instance.solve();
    watch.stop();
    if sat {
        let mut assignment_str = String::new();
        for (var, value) in &sat_instance.assignments {
            assignment_str.push_str(&format!(
                "{} {} ",
                var,
                if *value { "True" } else { "False" }
            ));
        }
        if assignment_str.ends_with(' ') {
            assignment_str = assignment_str.trim_end().to_string();
        }
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
