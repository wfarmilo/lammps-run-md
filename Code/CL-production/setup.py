import os
from pathlib import Path
import numpy as np
from ase.io import read as aread, write as awrite

#Run parameters
runtypes = ['p0m1', 'p1m0', 'p1m1']
run_nums = np.arange(5)

cwd = Path("./").resolve()
assert cwd.name == "CL-production", f"Wrong directory: {str(cwd)}"
data_dir = cwd.parents[1] /"Data"

#Set up output directories for classical production run

for rt in runtypes:
    for rn in run_nums:

        #Label for this run
        runlabel = f"{rt}-{rn:02d}"

        #Make output directory (if necessary)
        workdir = cwd /  f"out/{runlabel}"

        if not(workdir.exists()):
            workdir.mkdir()
            workdir.chmod(0o755)

            #Check that the output directory is linked up
            link_dir = data_dir / f"out/CL-production-out/{runlabel}"

            if not(link_dir.exists(follow_symlinks=False)):
                #Symlink output directory to pair in Data/out/CL-production-out
                os.symlink(workdir, link_dir, target_is_directory=True)

        #Get pdb file
        pdbin = data_dir /  f"input-pdb/{runlabel}.pdb"

        #Read in pdb file
        atoms = aread(pdbin)

        #Output in lammps form
        awrite(workdir / "initconf.data", 
               atoms, 
               format = "lammps-data", 
               atom_style = "atomic", 
               specorder = ["H", "O"], 
               masses = True)