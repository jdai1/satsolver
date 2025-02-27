use std::time::Instant;

const NANO: f64 = 1_000_000_000.0;

pub struct Clock {
    start_time: Option<Instant>,
    stop_time: Option<Instant>,
    running: bool,
}

impl Clock {
    pub fn new() -> Self {
        Clock {
            start_time: None,
            stop_time: None,
            running: false,
        }
    }

    pub fn reset(&mut self) {
        self.start_time = None;
        self.stop_time = None;
        self.running = false;
    }

    pub fn start(&mut self) {
        self.start_time = Some(Instant::now());
        self.running = true;
    }

    pub fn stop(&mut self) {
        if self.running {
            self.stop_time = Some(Instant::now());
            self.running = false;
        }
    }

    pub fn get_time(&self) -> f64 {
        match self.running {
            true => {
                if let Some(start_time) = self.start_time {
                    let elapsed = start_time.elapsed();
                    elapsed.as_nanos() as f64 / NANO
                } else {
                    0.0
                }
            },
            false => {
                if let Some(start_time) = self.start_time {
                    if let Some(stop_time) = self.stop_time {
                        let elapsed = stop_time.duration_since(start_time);
                        elapsed.as_nanos() as f64 / NANO
                    } else {
                        0.0
                    }
                } else {
                    0.0
                }
            }
        }
    }
}