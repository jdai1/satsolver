import time
from functools import wraps
from dataclasses import dataclass

DEBUG = False


@dataclass
class FunctionStats:
    count: int = 0
    time: float = 0


def track_call_and_time(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if func.__name__ not in self.function_stats:
            self.function_stats[func.__name__] = FunctionStats()
        self.function_stats[func.__name__].count += 1

        start_time = time.time_ns()
        result = func(self, *args, **kwargs)
        end_time = time.time_ns()

        self.function_stats[func.__name__].time += (
            end_time - start_time
        ) / 1000000000.0

        return result

    return wrapper

def debug_print(msg: str, level: int = 0) -> None:
    if DEBUG:
        space = level * "--"
        space += " " if level != 0 else ""
        print(f"{space}{msg}")
        

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
