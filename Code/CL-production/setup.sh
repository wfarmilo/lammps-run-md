#!/bin/bash

# Check directory
cd ../../Code/CL-production || exit 1
source /work/e898/shared/waf25/.venv/bin/activate

execdir=$(realpath "./")
templates_dir="${execdir}/templates"

#Get temperatures
temps=$(jq -r '.temperature[]' "${templates_dir}/production.json")

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
