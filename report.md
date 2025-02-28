### Mass Customization Report

Name: Julian Dai
CS Login: jkdai
Pseudonym: monkey

## Stragey

My implementation sticks faithfully to the classic DPLL algorithm discussed in class, consisting of:
- Unit Propagation (UP)
- Pure Literal Elimination (PLE)
- Branching + heuristics (e.g. DLCS, DLIS)

## Initial Implementation
The initial implementation consisted of a recursive DPLL algorithm implementing UP, PLE, and random branching in Python with simplistic data structures (i.e. only a list of clauses) that were copied on each branch. With this approach, I achieved a score of 4800, with 14/22 of the problems unsolved in the allotted 5 minutes. With some low-hanging engineering improvements (e.g. using list comprehension to copy data structures instead of copy()/deepcopy()), the score improved significantly — for example C168_128 decreased from 26.50s to 5.25s and C181_3151 decreased from 13.57s to 7.33s.

## (Attempted) Optimizations

I will now discuss (most of) the optimizations I implemented to varying degrees of success. 

## A Search Heuristic & Intelligent Data Structures

The first major improvement in my SAT solver came from 2 things:
1) Implementing DLCS/DLIS as a search heuristic
2) Improving the efficiency of unit propagation and pure literal elimination via intelligent data structures:
- unit_literals: list
- lit2clause: dict[int, set(int)]

While these data structures can be maintained with relatively low cost and speed up UP, PLE, and DLCS/DLIS, they must also be copied on every branching. However, the experimental results showed that the benefits introduced by these data structured outweighed the cost. This implementation produced a score of 2377.65s, with 6 unsolved CNF instances. Unsure what exactly to do next, I profiled my code by tracking time spent in relevant functions, observing that my SAT Solver spent the largest amount of times performing unit propagation and copying data structures. To further optimize my code, I attempted an implementation of watched literals, which theoretically speeds up UP and removes the need for the copying of some data structures.

## Watched Literals



## CDCL

## Python vs Rust


Time spent: ~ 30 hours