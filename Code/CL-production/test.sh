#!/bin/bash

# Directory check
cd ../../Code/CL-production/ || exit 1
execdir=$(realpath "./")

# Get project account from directory name
acct=$( pwd | awk -F'/' '{print $(NF-5)}')
if [[ "${acct}" == "e89" ]]; then acct="e89-camp"; fi

#Get defect types and run numbers from json file
temps=$(jq -r '.temperature[]' "${execdir}/templates/production.json")
dftypes=$(jq -r '.defect_types[]' "${execdir}/templates/production.json")
run_nums=$(jq -r '.run_indices[]' "${execdir}/templates/production.json")

dftype=p0m1
run=0
T=200

######################## setup.sh #################################

# Check directory
cd ../../Code/CL-production || exit 1
source /work/e898/shared/waf25/.venv/bin/activate

current_dir=$(realpath ".")
templates_dir="${current_dir}/templates"

outpref="prod-T${T}"

# Replace json values for setup.py
sed -e "s|XXXOUTPREFXXX|${outpref}|g"                    \
    -e "s|"temperature" : .*,|"temperature" : ${T},|g"   \
    "${templates_dir}/production.json" > "${templates_dir}/temp.json"

python setup.py 0 -ff "${templates_dir}/temp.json"

rm "${templates_dir}/temp.json"

########################## run.sh #################################

# Directory check
cd ../../Code/CL-production/ || exit 1
execdir=$(realpath "./")

# Get project account from directory name
acct=$( pwd | awk -F'/' '{print $(NF-5)}')
if [[ "${acct}" == "e89" ]]; then acct="e89-camp"; fi

dftype=p0m1
run=0
T=200

runpref="prod-T${T}"
folder="${dftype}-0${run}/${runpref}"
echo "Running ${runpref} from ${folder}"

# Change to work directory
workdir=$(realpath "../out/${folder}") || exit 1

cd $workdir || exit 1

runtime=20  # In minutes

sbatch  --time=$runtime \
        --qos=short \
        --account=${acct} \
        --output="${workdir}/slurm.log" \
        --job-name="${folder}" \
        "${execdir}/templates/submit.sh" ${runpref}

#Return to starting directory
cd "${execdir}"