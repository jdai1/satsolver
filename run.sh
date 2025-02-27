#!/bin/bash

########################################
############# CSCI 2951-O ##############
########################################
E_BADARGS=65
if [ $# -ne 1 ]
then
	echo "Usage: `basename $0` <input>"
	exit $E_BADARGS
fi
	
input=$1

# Update this file with instructions on how to run your code given an input


# python -m src.solver.sat.solve $input


for i in {1..15}
do
  echo "Run $i of 15"
  cd src/rust/dpll
  timeout 30s cargo run --release -- $1
  cd ../../..
done


