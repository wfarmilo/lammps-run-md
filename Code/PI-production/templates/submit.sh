#!/bin/bash

#SBATCH --job-name=ipi
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

# Get walltime for job
JOB_TIME=$3

# Determine how many cores each bead gets
cores_per_bead=$(( 128 / $nbeads ))

if [ $cores_per_bead -lt 1 ]; then
    echo "Too many beads ${nbeads} -> ${cores_per_bead}"
    exit 1
fi

# Find input files
lmpinput="input-${outprefix}.lmp"

if [ -s "RESTART" ]; then                   # First look for end of simulation (no overwriting)
    ipiinput="RESTART"
elif [ -s "${outprefix}.restart" ]; then    # Then look for checkpoint (maybe omit this step?)
    ipiinput="${outprefix}.restart"
else
    ipiinput="input-${outprefix}.xml"       # Then if neither exist use input
fi

# General substitution for node id
portnum=31415    
sed -i "s|address>.*<|address>${HOSTNAME}<|g" "${ipiinput}"     #match anything btwn address>___< and replace with node id
sed -i "s|ipi .*|ipi ${HOSTNAME} ${portnum}|g" "${lmpinput}"    #match anything after the field 'ipi' and replace with nid, portname

# Swap in for job time (in seconds)
SAFE_TIME=$(( ($JOB_TIME - 5) * 60 ))
sed -i "s|total_time>.*<|total_time>${SAFE_TIME}<|g" "${ipiinput}"

# Start ipi server
i-pi "${ipiinput}" &> "log.ipi" &

# Grab ipi process ID so we can cancel job later
IPI_PID=$!

# Give ipi server some time to boot up
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

# Wait until ipi server is done
wait "${IPI_PID}"

# Give LAMMPS some time to exit cleanly
sleep 30

# After ipi & LAMMPS are done, cancel itself
scancel "${SLURM_JOB_ID}"