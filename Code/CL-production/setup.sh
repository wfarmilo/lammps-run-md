#!/bin/bash

# Check directory
cd ../../Code/CL-production || exit 1
source /work/e898/shared/waf25/.venv/bin/activate

current_dir=$(realpath ".")
templates_dir="${current_dir}/templates"

#Get temperatures
temps=$(jq -r '.temperatures[]' "${execdir}/templates/production.json")

for T in ${temps[*]}
do

        outpref="prod-T${T}"

        # Replace json values for setup.py
        sed -e "s|XXXOUTPREFXXX|${outpref}|g"                    \
            -e "s|\"temperature\" : .*,|\"temperature\" : ${T},|g"   \
            "${templates_dir}/production.json" > "${templates_dir}/temp.json"

        python setup.py 0 -ff "${templates_dir}/temp.json"

        rm "${templates_dir}/temp.json"
done
