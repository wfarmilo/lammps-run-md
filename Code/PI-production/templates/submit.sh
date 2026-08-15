#!/bin/bash

#SBATCH --job-name=ipi
#SBATCH --nodes=1
#SBATCH --ntasks=128
#SBATCH --ntasks-per-node=128
#SBATCH --cpus-per-task=1
#SBATCH --time=24:00:00
#SBATCH --account=e898
#SBATCH --partition=standard
#SBATCH --qos=standard

export WORKDIR=$(realpath "/work/e898/e898/${USER}")

module load PrgEnv-gnu
export CRAYPE_LINK_TYPE=dynamic

#Source i-pi (and python ig)
source "${WORKDIR}/.venv/bin/activate"

# Get LAMMPS executable
LAMMPS="${WORKDIR}/symmetrix-lammps/lammps/build/lmp"

# Direct loader to shared libraries
export LD_LIBRARY_PATH="${WORKDIR}/symmetrix-lammps/lammps/build:${LD_LIBRARY_PATH}"

# Ensure OMP_NUM_THREADS is consistent with cpus-per-task above
export OMP_NUM_THREADS=1
export SRUN_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK}

# Get run name
outprefix=$1

# Get total bead count (for parallelization)
nbeads=$2
cores_per_bead=$(( 128 / $nbeads ))

if [ $cores_per_bead -lt 1 ]; then
    echo "Too many beads ${nbeads} -> ${cores_per_bead}"
    exit 1
fi

# Find input files
lmpinput="input-${outprefix}.lmp"

if [ -e "${outprefix}.restart" ]; then
    ipiinput="${outprefix}.restart"
else
    ipiinput="input-${outprefix}.xml"
fi

# General substitution for node id
portnum=31415    
sed -i "s|address>.*<|address>${HOSTNAME}<|g" "${ipiinput}"     #match anything btwn address>___< and replace with node id
sed -i "s|ipi .*|ipi ${HOSTNAME} ${portnum}|g" "${lmpinput}"    #match anything after the field 'ipi' and replace with nid, portname

# Start ipi server
i-pi "${ipiinput}" &> log.ipi &
sleep 20

# Run lammps, split over cores
for (( i=0; i<nbeads; i++ )); do
    if [ "$i" -eq 0 ]; then
        logflag="log-${outprefix}.lammps"
    else
        logflag="none"
    fi

    #Run, split core for beads
    srun    --exact  \
            --ntasks=${cores_per_bead}  \
            --ntasks-per-node=${cores_per_bead} \
            --mem=$(( $cores_per_bead * 1500 ))M \
            ${LAMMPS} -log ${logflag} -in "${lmpinput}" &


done
wait