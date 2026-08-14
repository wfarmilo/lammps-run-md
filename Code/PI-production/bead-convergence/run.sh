#!/bin/bash

# Directory check
cd ../../PI-production/bead-convergence || exit 1
execdir=$(realpath "../")

#Get run parameters (must be same as setup.sh)
temps=(200) #(200 250 300)
beads=(1) #(1 2 4 8 16 32 64)
pitypes=(PILE) #(PILE ECON)

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
                    workdir=$(realpath "../out/${folder}")

                    cd $workdir || exit 1

                    runtime=$(( 60 * $nbeads ))

                    sbatch --time=$runtime --qos=standard --output="${workdir}/slurm.log" "${execdir}/templates/submit.sh" ${runpref}

                    #Return to starting directory
                    cd "${execdir}/bead-convergence"

                done
            done
        done
    done
done