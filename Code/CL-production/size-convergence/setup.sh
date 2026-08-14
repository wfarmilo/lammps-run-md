#!/bin/bash

# Check directory
cd ../../CL-production/size-convergence || exit 1
source ../../../../.venv/bin/activate

# Switch to CL-production parent dir
cd ..

current_dir=$(realpath ".")
templates_dir="${current_dir}/templates"

# Create temporary run parameters
temps=(200) #(200 250 300)
pdb_exts=("") #("64" "" "128")  # "" means 96 here


for T in ${temps[*]}
do
    for pdbin in ${pdb_exts[*]}
    do
        pdbname=${pdbin}
        if [ -z ${pdbin} ]; then pdbname="96"

        outpref="conv-${pi}-T${T}-N${pdbname}"

        sed -e "s|XXXPDBNAMEXXX|${pdbname}|g"       \
            -e "s|XXXTEMPXXX|${T}|g"            \
            -e "s|XXXOUTPREFXXX|${outpref}|g"   \
            "${templates_dir}/size-convergence.json" > "${templates_dir}/temp.json"

        python setup.py 0 -ff "${templates_dir}/temp.json"

        rm "${templates_dir}/temp.json"
    done
done