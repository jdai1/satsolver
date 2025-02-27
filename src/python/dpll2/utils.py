from typing import Set
import time
from .sat_instance import SATInstance2
from dataclasses import dataclass
from functools import wraps

DEBUG = False

@dataclass
class FunctionStats:
    count: int = 0
    time: float = 0


# UTILS

def debug_print(msg: str, level: int = 0) -> None:
    if DEBUG:
        space = level * "--"
        space += " " if level != 0 else ""
        print(f"{space}{msg}")


def track_call_and_time(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.function_stats[func.__name__].count += 1

        start_time = time.time()
        result = func(self, *args, **kwargs)
        end_time = time.time()

        self.function_stats[func.__name__].time += end_time - start_time

        return result

    return wrapper

class DimacsParser:
    @staticmethod
    def parse_cnf_file(file_name: str):
        sat_instance = None
        try:
            with open(file_name, 'r') as file:
                lines = file.readlines()

                start_index = -1
                problem_line = None
                for i in range(len(lines)):
                    line = lines[i]
                    tokens = line.strip().split()
                    if not tokens or tokens[0] == 'c':
                        continue
                    problem_line = tokens
                    start_index = i + 1
                    break
                
                if not problem_line or problem_line[0] != 'p':
                    raise ValueError("Error: DIMACS file does not have problem line")
                
                if problem_line[1] != 'cnf':
                    raise ValueError("Error: DIMACS file format is not cnf")
                
                num_vars = int(problem_line[2])
                num_clauses = int(problem_line[3])
                sat_instance = SATInstance2(num_vars, num_clauses)
                
                # Parse clauses
                clause: Set[int] = set()
                for i in range(start_index, len(lines)):
                    line = lines[i]
                    tokens = line.strip().split()
                    
                    if not tokens or tokens[0] == 'c':
                        continue
                        
                    if tokens[-1] != '0':
                        raise ValueError(f"Error: clause line does not end with 0: {tokens}")
                    
                    for token in tokens[:-1]:
                        if token:
                            literal = int(token)
                            clause.add(literal)
                            sat_instance.add_variable(literal)
                    
                    sat_instance.add_clause(clause)
                    clause = set()
                    
        except FileNotFoundError:
            raise FileNotFoundError(f"Error: DIMACS file is not found {file_name}")
            
        return sat_instance

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
