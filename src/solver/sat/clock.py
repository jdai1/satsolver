import time

NANO = 1000000000.0

class Clock:
    def __init__(self):
        self.start_time = 0
        self.stop_time = 0
        self.running = False
        
    
    def reset(self):
        self.start_time = 0
        self.running = False
    
    def start(self):
        self.start_time = time.time_ns()
        self.running = True
    
    def stop(self):
        if self.running:
            self.stop_time = time.time_ns()
            self.running = False
    
    def get_time(self) -> float:
        if self.running:
            elapsed = (time.time_ns() - self.start_time) / NANO
        else:
            elapsed = (self.stop_time - self.start_time) / NANO
        return elapsed
