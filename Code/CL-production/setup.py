import argparse

parser = argparse.ArgumentParser()

parser.add_argument("temp", help = "Simulation temperature", type = int)

args=parser.parse_args()

import os
from pathlib import Path
import numpy as np
from ase.io import read as aread, write as awrite

#Run parameters
runtypes = ['p0m1', 'p1m0', 'p1m1']
run_nums = np.arange(5)

step_size = 8   #4fs between frames
temperature = args.temp
outprefix = f'T{temperature}'

cwd = Path("./").resolve()
assert cwd.name == "CL-production", f"Wrong directory: {str(cwd)}"
data_dir = cwd.parents[1] /"Data"
templates_dir = cwd / "templates"

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

            if not(link_dir.is_symlink()):
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

        #Get lammps input
        lammps_inp = templates_dir / "input.lmp"

        with open(lammps_inp, "r") as li:
            inptext = li.read()

        #Swap out placeholders
        inptext = inptext.replace(f"XXXTEMPXXX", f"{temperature}")
        inptext = inptext.replace(f"XXXSTEPSIZEXXX", f"{step_size}")
        inptext = inptext.replace(f"XXXMODELPATHXXX", str(templates_dir / "ch2o-dens-inv_swa-1-8.json"))
        inptext = inptext.replace(f"XXXOUTPREFXXX", outprefix)

        #Save lammps input
        lammps_inp_out = workdir / f"input-{outprefix}.lmp"
        with open(lammps_inp_out, "w") as lio:
            lio.write(inptext)