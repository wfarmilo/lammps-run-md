\#!/bin/bash

# Directory check
cd ../../PI-production/bead-convergence || exit 1
execdir=$(realpath "../")

# Get project account from directory name
acct=$( pwd | awk -F'/' '{print $(NF-5)}')
if [[ "${acct}" == "e89" ]]; then acct="e89-camp"; fi

#Get run parameters (must be same as setup.sh)
temps=(200) #(200 250 300)
beads=(2 8 32) #(1 2 4 8 16 32 64)
pitypes=(PILE ECON) #(PILE ECON)

#Get defect types and run numbers from json file
dftypes=$(jq -r '.defect_types[]' "${execdir}/templates/bead-convergence.json")
run_nums=$(jq -r '.run_indices[]' "${execdir}/templates/bead-convergence.json")

for dftype in ${dftypes}
do
    for run in ${run_nums}
    do
        for pitype in ${pitypes[*]}
        do
            for temp in ${temps[*]}
            do
                for nbeads in ${beads[*]}
                do
                    runpref="conv-${pitype}-T${temp}-P${nbeads}"
                    folder="${dftype}-0${run}/${runpref}"
                    echo "Running ${runpref} from ${folder}"

                    # Change to work directory
                    workdir=$(realpath "../out/${folder}") || exit 1

                    cd $workdir || exit 1

                    runtime=$(( 60 * 20 ))  # In minutes

                    sbatch  --time=$runtime \
                            --qos=taskfarm \
                            --account=${acct} \
                            --output="${workdir}/slurm.log" \
                            --job-name="${folder}" \
                            "${execdir}/templates/submit.sh" ${runpref} ${nbeads} ${runtime}

                    #Return to starting directory
                    cd "${execdir}/bead-convergence"

                done
            done
        done
    done
done
