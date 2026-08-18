#!/bin/bash

# Check directory
cd ../../PI-production/bead-convergence || exit 1
source /work/e898/shared/waf25/.venv/bin/activate

# Switch to PI-production parent dir
cd ..

current_dir=$(realpath ".")
templates_dir="${current_dir}/templates"

# Create temporary run parameters
temps=(200) #(200 300)
beads=(2 8 32) #(1 2 4 8 16 32 64)
pitypes=(PILE ECON) #(PILE ECON)


for pi in ${pitypes[*]}
do
    for T in ${temps[*]}
    do
        for P in ${beads[*]}
        do
            outpref="conv-${pi}-T${T}-P${P}"

            sed -e "s|XXXPIMDTYPEXXX|${pi}|g"       \
                -e "s|XXXTEMPXXX|${T}|g"            \
                -e "s|XXXNBEADSXXX|${P}|g"          \
                -e "s|XXXOUTPREFXXX|${outpref}|g"   \
                "${templates_dir}/bead-convergence.json" > "${templates_dir}/temp.json"

            python setup.py 0 0 0 -ff "${templates_dir}/temp.json"

            rm "${templates_dir}/temp.json"
        done
    done
done
