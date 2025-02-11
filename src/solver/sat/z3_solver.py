from z3 import *
import sys

files = [
    "C1065_064.cnf",
    "C1065_082.cnf",
    "C140.cnf",
    "C1597_024.cnf",
    "C1597_060.cnf",
    "C1597_081.cnf",
    "C168_128.cnf",
    "C175_145.cnf",
    "C181_3151.cnf",
    "C200_1806.cnf",
    "C208_120.cnf",
    "C208_3254.cnf",
    "C210_30.cnf",
    "C210_55.cnf",
    "C243_188.cnf",
    "C289_179.cnf",
    "C459_4675.cnf",
    "C53_895.cnf",
    "U50_1065_038.cnf",
    "U50_1065_045.cnf",
    "U50_4450_035.cnf",
    "U75_1597_024.cnf",
]


answers = {}
for f in files:
    s = Solver()
    s.from_file(f"../../../input/{f}")
    print(f, s.check())

print(answers)



