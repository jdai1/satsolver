from typing import Set
from .dpll1.sat_instance import SATInstance1
from .dpll2.sat_instance import SATInstance2
from .dpll3.sat_instance import SATInstance3

class DimacsParser:
    @staticmethod
    def parse_cnf_file(file_name: str, version: int):
        sat_instance = None

        sat_instance_class = None
        if version == 1:
            sat_instance_class = SATInstance1
        elif version == 2:
            sat_instance_class = SATInstance2
        elif version == 3:
            sat_instance_class = SATInstance3
        else:
            raise Exception(f"bad version: {version}")
        
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
                sat_instance = sat_instance_class(num_vars, num_clauses)
                
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
