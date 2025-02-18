#!/bin/bash

########################################
############# CSCI 2951-O ##############
########################################
E_BADARGS=65
if [ $# -ne 3 ]
then
    echo "Usage: `basename $0` <inputFolder/> <timeLimit> <logFile>"
    echo "Description:"
    echo -e "\t This script make calls to ./run.sh for all the files in the given inputFolder/"
    echo -e "\t Each run is subject to the given time limit in seconds."
    echo -e "\t Last line of each run is appended to the given logFile."
    echo -e "\t If a run fails, due to the time limit or other error, the file name is appended to the logFile with --'s as time and result. "
    echo -e "\t If the logFile already exists, the run is aborted."
    exit $E_BADARGS
fi

# Check if GNU Parallel is installed
if ! command -v parallel &> /dev/null; then
    echo "GNU Parallel is required but not installed. Please install it first."
    exit 1
fi

# Parameters
inputFolder=$1
timeLimit=$2
logFile=$3

# Append slash to the end of inputFolder if it does not have it
lastChar="${inputFolder: -1}"
if [ "$lastChar" != "/" ]; then
    inputFolder=$inputFolder/
fi

# Terminate if the log file already exists
[ -f $logFile ] && echo "Logfile $logFile already exists, terminating." && exit 1

# Create the log file
touch $logFile
touch $logFile.verbose

# Function to process a single file
process_file() {
    local fullFileName="$1"
    local timeLimit="$2"
    local logFile="$3"
    
    echo "Running $fullFileName"
    local tmpfile=$(mktemp)
    
    if timeout "${timeLimit}s" ./run.sh "$fullFileName" > "$tmpfile" 2>/dev/null; then
        # Run is successful
        tail -n 1 "$tmpfile" >> "$logFile"
        cat "$tmpfile" >> "$logFile.verbose"
    else
        # Run failed, record the instanceName with no solution
        echo Error
        local instance=$(basename "$fullFileName")
        echo "{\"Instance\": \"$instance\", \"Time\": \"--\", \"Result\": \"--\"}" >> "$logFile"
    fi
    rm -f "$tmpfile"
}
export -f process_file
export timeLimit
export logFile

# Run on every file in parallel
find "$inputFolder" -maxdepth 1 -type f -print0 | \
    parallel -0 process_file {} "$timeLimit" "$logFile"
