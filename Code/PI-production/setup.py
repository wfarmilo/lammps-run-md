import argparse

parser = argparse.ArgumentParser()

parser.add_argument("temp", help = "Simulation temperature", type = int)
parser.add_argument("ipi_type", help = "Style of PIMD", type = str)
parser.add_argument("bead_count", help = "Number of PIMD beads", type = int)
args=parser.parse_args()


import os
from pathlib import Path
import numpy as np
from ase.io import read as aread, write as awrite

#Run parameters
runtypes = ['p0m1', 'p1m0', 'p1m1']
run_nums = np.arange(5)

step_size = 16      # 4fs between frames
Nt = 1000000        # 500ps of data
temperature = args.temp
pimd_type = args.ipi_type
P = args.bead_count
outprefix = f'{pimd_type}-T{temperature}-P{P}'

cwd = Path("./").resolve()
assert cwd.name == "PI-production", f"Wrong directory: {str(cwd)}"
data_dir = cwd.parents[1] /"Data"
templates_dir = cwd / "templates"

#Set up output directories for classical production run

for rt in runtypes:
    for rn in run_nums:

        #Label for this run
        runlabel = f"{pimd_type}-T{temperature}-P{P}"

        #Make output directory (if necessary)
        workdir = cwd /  f"out/{rt}-{rn:02d}/{runlabel}"

        if not(workdir.exists()):
            workdir.mkdir(parents=True)
            workdir.chmod(0o755)

            #Check that the output directory is linked up
            link_dir = data_dir / f"out/PI-production-out/{rt}-{rn:02d}/{runlabel}"

            if not(link_dir.is_symlink()):
                #Symlink output directory to pair in Data/out/PI-production-out
                os.symlink(workdir, link_dir, target_is_directory=True)
        else:
            raise Exception(f"Directory {str(workdir)} exists")

        #Get pdb file
        pdbin = data_dir /  f"input-pdb/{rt}-{rn:02d}.pdb"

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

        #Get ipi input
        ipi_inp = templates_dir / f"{pimd_type}.xml"

        edit_inputs = [lammps_inp, ipi_inp]
        inptext = ['', '']
        for ini, inp in enumerate(edit_inputs):
            with open(inp, "r") as ii:
                inptext[ini] = ii.read()

            #Swap out placeholders

            #Global
            inptext[ini] = inptext[ini].replace(f"XXXTEMPXXX", f"{temperature}")
            inptext[ini] = inptext[ini].replace(f"XXXOUTPREFXXX", outprefix)
            inptext[ini] = inptext[ini].replace(f"XXXNSTEPSXXX", f"{Nt}")

            #LAMMPS input file
            inptext[ini] = inptext[ini].replace(f"XXXSTEPSIZEXXX", f"{step_size}")
            inptext[ini] = inptext[ini].replace(f"XXXMODELPATHXXX", str(templates_dir / "ch2o-dens-inv_swa-1-8.json"))

            #ipi input file
            inptext[ini] = inptext[ini].replace(f"XXXPROPSTRIDEXXX", f"{100*step_size}")
            inptext[ini] = inptext[ini].replace(f"XXXTRAJSTRIDEXXX", f"{step_size}")
            inptext[ini] = inptext[ini].replace(f"XXXCHECKPTSTRIDEXXX", f"{step_size}")
            inptext[ini] = inptext[ini].replace(f"XXXNBEADSXXX", f"{P}")

        #Copy over pdb file (and reformat for i-pi)
        with open(pdbin, "r") as fpdb:
            pdb_lines = fpdb.readlines()

        #Filter out MODEL and ENDMDL
        filtered = [line for line in pdb_lines if not(line.startswith("MODEL")) and not(line.startswith("ENDMDL"))]

        with open(workdir / "initconf.pdb", "w") as pdbo:
            #Add title line
            pdbo.write(f"TITLE <{rt}-{rn:02d}>" + r"position{angstrom} cell{angstrom}")

            pdbo.writelines(filtered)


        #Save lammps input
        lammps_inp_out = workdir / f"input-{outprefix}.lmp"
        with open(lammps_inp_out, "w") as lio:
            lio.write(inptext[0])

        #Save ipi input
        ipi_inp_out = workdir / f"input-{outprefix}.xml"
        with open(ipi_inp_out, "w") as iio:
            iio.write(inptext[1])