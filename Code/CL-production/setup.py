import argparse

parser = argparse.ArgumentParser()

parser.add_argument("temp", help = "Simulation temperature", type = int)
parser.add_argument("-o", "--output", help="Name of output type directory (defaults to PIMD-TXXX-PYY)")
parser.add_argument("-i", "--input", default = 'XXXDFXXX', help="Name of input pdb file from Data/input-pdb (defaults to pXmY-ZZ.pdb). Will replace string XXXDFXXX with pXmY-ZZ.")
parser.add_argument("-q", "--quantity", help="Number of runs to do", default = 5, type = int)
parser.add_argument("-ff", "--from_file", help = "Read all run parameters from a file")

args=parser.parse_args()

import os
from pathlib import Path
import numpy as np
from ase.io import read as aread, write as awrite
import json

if args.from_file == None:
    #Run parameters
    runtypes = ['p0m1', 'p1m0', 'p1m1']
    run_nums = np.arange(5)

    step_size = 8   #4fs between frames
    Nt = 1000000        # 500ps of data
    temperature = args.temp
    outprefix = f'T{temperature}'
    pdbinput = args.input

else:
    #Read from json file
    with open(args.from_file) as f:
        runparams = json.loads(f.read())

    runtypes = runparams["defect_types"]
    run_nums = runparams["run_indices"]

    step_size = runparams["step_size"]
    Nt = runparams["step_count"]
    temperature = int(runparams["temperature"])
    outprefix = runparams["output_name"]
    pdbinput = runparams["pdb_input_name"]

cwd = Path("./").resolve()
assert cwd.name == "CL-production", f"Wrong directory: {str(cwd)}"
data_dir = cwd.parents[1] /"Data"
templates_dir = cwd / "templates"
model_path = "/work/e898/shared/waf25/mace-models/ch2o-dens-inv_swa-1-8.json"


#Set up output directories for classical production run

for rt in runtypes:
    for rn in run_nums:

        #Make output directory (if necessary)
        workdir = cwd /  f"out/{rt}-{rn:02d}/{outprefix}"

        print(f"Making directory {str(workdir.absolute())}")

        if not(workdir.exists()):
            workdir.mkdir(parents=True)
            workdir.chmod(0o755)

            #Check that the output directory is linked up
            data_parent = data_dir / f"out/CL-production-out/{rt}-{rn:02d}"
            if not(data_parent.exists()):
                data_parent.mkdir(parents=True)
                data_parent.chmod(0o755)

            link_dir = data_parent / f"{outprefix}"

            if not(link_dir.is_symlink()):
                #Symlink output directory to pair in Data/out/CL-production-out
                os.symlink(workdir, link_dir, target_is_directory=True)

        else:
            raise Exception(f"Directory {str(workdir)} exists")

        #Get pdb file
        pdbname = pdbinput.replace('XXXDFXXX', f"{rt}-{rn:02d}")
        pdbin = data_dir /  f"input-pdb/{pdbname}.pdb"

        print(f"Creating inputs from {str(pdbin.absolute())}")

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
        input_names = ["input", "input-restart"]

        for name in input_names:
            lammps_inp_in = templates_dir / f"{name}.lmp"

            with open(lammps_inp_in, "r") as li:
                inptext = li.read()

            #Swap out placeholders
            inptext = inptext.replace(f"XXXTEMPXXX", f"{temperature}")
            inptext = inptext.replace(f"XXXSTEPSIZEXXX", f"{step_size}")
            inptext = inptext.replace(f"XXXMODELPATHXXX", str(model_path))
            inptext = inptext.replace(f"XXXOUTPREFXXX", outprefix)
            inptext = inptext.replace(f"XXXNSTEPSXXX", f"{Nt}")

            #Save lammps input
            lammps_inp_out = workdir / f"{name}-{outprefix}.lmp"
            with open(lammps_inp_out, "w") as lio:
                lio.write(inptext)