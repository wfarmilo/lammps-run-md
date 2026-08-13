#!/bin/bash

# Directory check
cd ../../Code/PI-production || exit 1
execdir=$(realpath "./")


pitype=$1
temp=$2

runpref="${pitype}-T${temp}"
echo "Running ${runpref}"


# Change to work directory
workdir=$(realpath "./out/${runpref}/")

cd $workdir || exit 1

sbatch --time=20 --qos=short "${execdir}/templates/submit.sh" ${runpref}