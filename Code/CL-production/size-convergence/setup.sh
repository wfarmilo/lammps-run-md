#!/bin/bash

# Check directory
cd ../../CL-production/size-convergence || exit 1
source /work/e898/shared/waf25/.venv/bin/activate

# Switch to CL-production parent dir
cd ..

current_dir=$(realpath ".")
templates_dir="${current_dir}/templates"

#Get run parameters
temps=$(jq -r '.temperature[]' "${templates_dir}/size-convergence.json")
pdb_exts=$(jq -r '.pdb_sizes[]' "${templates_dir}/size-convergence.json")


for T in ${temps[*]}
do
    for pdbin in ${pdb_exts[*]}
    do

        # Output file name
        outpref="conv-T${T}-N${pdbin}"

        # Use pXmY placeholder for setup.py
        pdbname="XXXDFXXX-N${pdbin}"

        # Original size does not have N specifier
        if [ ${pdbin} -eq 96 ]; then 
            pdbname="XXXDFXXX"
        fi

        sed -e "s|XXXPDBNAMEXXX|${pdbname}|g"   \
            -e "s|XXXTEMPXXX|${T}|g"            \
            -e "s|XXXOUTPREFXXX|${outpref}|g"   \
            "${templates_dir}/size-convergence.json" > "${templates_dir}/temp.json"

        python setup.py 0 -ff "${templates_dir}/temp.json"

        rm "${templates_dir}/temp.json"
    done
done