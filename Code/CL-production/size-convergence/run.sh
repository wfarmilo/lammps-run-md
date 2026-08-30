#!/bin/bash

# Directory check
cd ../../CL-production/size-convergence || exit 1
cd ..

execdir=$(realpath "./")

# Get project account from directory name
acct=$( pwd | awk -F'/' '{print $(NF-5)}')
if [[ "${acct}" == "e89" ]]; then acct="e89-camp"; fi

#Get defect types and run numbers from json file
temps=$(jq -r '.temperature[]' "${execdir}/templates/size-convergence.json")
dftypes=$(jq -r '.defect_types[]' "${execdir}/templates/size-convergence.json")
run_nums=$(jq -r '.run_indices[]' "${execdir}/templates/size-convergence.json")
sizes=$(jq -r '.pdb_sizes[]' "${execdir}/templates/size-convergence.json")

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
            workdir=$(realpath "./out/${folder}") || exit 1

            cd $workdir || exit 1

            runtime=$(( 60 * 24 ))  # In minutes

            restartfile=$(ls -t final-${runpref}.*.restart | head -n 1)
            if [ -e "${restartfile}" ]; then
                filein="input-restart-${runpref}.lmp"
                sed -i "s|read_restart .*|read_restart ${restartfile}|g" "${filein}"
            else
                filein="input-${runpref}.lmp"
            fi


            sbatch  --time=$runtime     \
                    --qos=taskfarm      \
                    --account=${acct}   \
                    --output="${workdir}/slurm.log" \
                    --job-name="${folder}"          \
                    "${execdir}/templates/submit.sh" ${filein} ${runtime}

            #Return to starting directory
            cd "${execdir}"
        done
    done
done

