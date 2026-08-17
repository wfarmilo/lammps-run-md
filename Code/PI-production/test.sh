#!/bin/bash

# Directory check
cd ../../Code/PI-production || exit 1
execdir=$(realpath "./")

# Get project account from directory name
acct=$( pwd | awk -F'/' '{print $(NF-4)}')
if [[ "${acct}" == "e89" ]]; then acct="e89-camp"; fi

dftype=$1
temp=$2
pitype=$3
nbeads=$4

runpref="${pitype}-T${temp}-P${nbeads}"
folder="${dftype}-00/${runpref}"
echo "Running ${runpref} from ${folder}"


# Change to work directory
workdir=$(realpath "./out/${folder}")

cd $workdir || exit 1

sbatch --time=20 --qos=short --account=${acct} --output="${workdir}/slurm.log" "${execdir}/templates/submit.sh" ${runpref} ${nbeads} 20