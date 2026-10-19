#!/bin/bash

# Directory check
cd ../../PI-production/bead-convergence || exit 1
execdir=$(realpath "../")

# Get project account from directory name
acct=$( pwd | awk -F'/' '{print $(NF-5)}')
if [[ "${acct}" == "e89" ]]; then acct="e89-camp"; fi

#Get defect types and run numbers from json file
jsonfile="${execdir}/templates/production.json"
mapfile -t beads < <(jq -r '.num_beads[]' "${jsonfile}")
mapfile -t temps < <(jq -r '.temperature[]' "${jsonfile}")
mapfile -t dftypes < <(jq -r '.defect_types[]' "${jsonfile}")
mapfile -t run_nums < <(jq -r '.run_indices[]' "${jsonfile}")

for dftype in "${dftypes[@]}"
do
    for run in "${run_nums[@]}"
    do
        for i in "${!temps[@]}"
        do
            temp="${temps[i]}"
            nbeads="${beads[i]}"

            runpref="prod-T${temp}-P${nbeads}"
            folder="${dftype}-0${run}/${runpref}"
            echo "Running ${runpref} from ${folder}"

            # Change to work directory
            workdir=$(realpath "../out/${folder}") || exit 1

            cd $workdir || exit 1

            runtime=$(( 60 * 22 ))  # In minutes

            sbatch  --time=$runtime         \
                    --qos=taskfarm          \
                    --account=${acct}       \
                    --output="${workdir}/slurm.log" \
                    --job-name="${folder}"  \
                    "${execdir}/templates/submit.sh" ${runpref} ${nbeads} ${runtime}

            #Return to starting directory
            cd "${execdir}/bead-convergence"

        done
    done
done