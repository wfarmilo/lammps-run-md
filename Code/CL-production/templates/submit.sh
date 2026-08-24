#!/bin/bash

##SBATCH --job-name=Cl-production
#SBATCH --nodes=1
#SBATCH --ntasks=128
#SBATCH --ntasks-per-node=128
#SBATCH --cpus-per-task=1
#SBATCH --account=e898
#SBATCH --partition=standard
#SBATCH --qos=standard


export WORKDIR=$(realpath "/work/e898/shared/waf25")

module load PrgEnv-gnu
export CRAYPE_LINK_TYPE=dynamic

# Get LAMMPS executable
LAMMPS="${WORKDIR}/symmetrix-lammps/lammps/build/lmp"

# Direct loader to shared libraries
export LD_LIBRARY_PATH="${WORKDIR}/symmetrix-lammps/lammps/build:${LD_LIBRARY_PATH}"

# Ensure OMP_NUM_THREADS is consistent with cpus-per-task above
export OMP_NUM_THREADS=1
export SRUN_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK}

# Get input file name
inputname=$1

# Get walltime (input in minutes, convert to seconds)
walltime=$2
safe_time=$(( ($walltime - 5) * 60 ))

# Find input files
lmpinput="${inputname}"

if [ ! -e ${lmpinput} ]; then
    scancel $SLURM_JOB_ID
    exit 1
fi

# Sub in safe time
sed -i "s|timer timeout .* every|timer timeout ${safe_time} every|g" "${lmpinput}"

# Run lammps
srun ${LAMMPS} -in "${lmpinput}" &

wait