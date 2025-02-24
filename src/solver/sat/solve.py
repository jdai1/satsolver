#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from .dimacs_parser import DimacsParser
from .clock import Clock
from .dpll1.dpll_solver import dpll_solve
from .dpll2.dpll_solver2 import dpll_solve2
from .dpll3.dpll_solver3 import dpll_solve3
from pprint import pprint


def main():
    """Usage example: read a given cnf instance file to create a simple sat instance object and print out its parameter fields."""

    if len(sys.argv) < 2:
        print("Usage: python main.py <cnf file>")
        return

    input_file = sys.argv[1]
    filename = Path(input_file).name

    watch = Clock()
    watch.start()

    try:
        instance = DimacsParser.parse_cnf_file(input_file, version=2)
        
        watch.stop()
        print(
            f'{{"Instance": "{filename}", "Time": {watch.get_time():.2f}, "Result": "--"}}'
        )

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

    assert instance.num_vars > 0
    assert instance.num_clauses > 0

    watch = Clock()
    watch.start()
    sat, assignments = dpll_solve2(sat_instance=instance) # type: ignore
    watch.stop()

    res = {
        "Instance": filename,
        "Time": f"{watch.get_time():.2f}",
        "Result": "SAT" if sat else "UNSAT",
    }
    if sat:
        assignment_list = []
        for v, a in assignments.items():
            assignment_list.append(str(v))
            assignment_list.append(str(a))
        res["Solution"] = " ".join(assignment_list)
        
    print("Result:", "SAT" if sat else "UNSAT")
    if sat and not instance.check(): # type: ignore
        print("Incorrect assignment")

    pprint(instance.function_stats)
    print("Total time spent in watched functions:", sum([x.time for x in instance.function_stats.values()]))
    print(json.dumps(res))
    


if __name__ == "__main__":
    main()
