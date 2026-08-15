#!/bin/bash

#SBATCH --job-name=run-lammps-md
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=128
#SBATCH --cpus-per-task=32
#SBATCH --time=06:00:00
#SBATCH --account=e898
#SBATCH --partition=standard
#SBATCH --qos=standard
#SBATCH --output=run-lammps.out


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

# Get run name
outprefix=$1

# Find input files
lmpinput="input-${outprefix}.lmp"

# Run lammps
srun ${LAMMPS} -in "${lmpinput}" &

wait