#!/bin/bash

################### setup for fake run ###################

# Directory check
cd ../../Code/CL-production/ || exit 1
execdir=$(realpath "./")

# Get project account from directory name
acct=$( pwd | awk -F'/' '{print $(NF-5)}')
if [[ "${acct}" == "e89" ]]; then acct="e89-camp"; fi

dftype=p0m1
run=0
T=200

############ run.sh execution line starts here ############

runpref="prod-T${T}"
folder="${dftype}-0${run}/${runpref}"
echo "Running ${runpref} from ${folder}"

# Change to work directory
workdir=$(realpath "./out/${folder}") || exit 1

cd $workdir || exit 1

runtime=$(( 20 ))  # In minutes

restartfile=$(ls -t final-${runpref}.*.restart | head -n 1 2>/dev/null)
if [ -e "${restartfile}" ]; then
    filein="input-restart-${runpref}.lmp"
    sed -i "s|read_restart .*|read_restart ${restartfile}|g" "${filein}"
else
    filein="input-${runpref}.lmp"
fi


sbatch  --time=$runtime \
        --qos=short \
        --account=${acct} \
        --output="${workdir}/slurm.log" \
        --job-name="${folder}" \
        "${execdir}/templates/submit.sh" ${filein} ${runtime}

#Return to starting directory
cd "${execdir}"