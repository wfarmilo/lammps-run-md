#!/bin/bash

# Directory check
cd ../../Code/CL-production/ || exit 1
execdir=$(realpath "./")

# Get project account from directory name
acct=$( pwd | awk -F'/' '{print $(NF-5)}')
if [[ "${acct}" == "e89" ]]; then acct="e89-camp"; fi

#Get defect types and run numbers from json file
temps=$(jq -r '.temperatures[]' "${execdir}/templates/production.json")
dftypes=$(jq -r '.defect_types[]' "${execdir}/templates/production.json")
run_nums=$(jq -r '.run_indices[]' "${execdir}/templates/production.json")

for dftype in ${dftypes}
do
    for run in ${run_nums}
    do
        for T in ${temps}
        do
            runpref="prod-T${T}"
            folder="${dftype}-0${run}/${runpref}"
            echo "Running ${runpref} from ${folder}"

            # Change to work directory
            workdir=$(realpath "../out/${folder}") || exit 1

            cd $workdir || exit 1

            runtime=$(( 60 * 24 ))  # In minutes

            sbatch  --time=$runtime \
            --qos=lowpriority \
            --account=${acct} \
            --output="${workdir}/slurm.log" \
            --job-name="${folder}" \
            "${execdir}/templates/submit.sh" ${runpref}

            #Return to starting directory
            cd "${execdir}"
        done
    done
done

