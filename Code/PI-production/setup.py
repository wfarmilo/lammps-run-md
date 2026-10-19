import argparse

parser = argparse.ArgumentParser()
parser.add_argument("template_file", help = "Read all run parameters from a file")
args=parser.parse_args()


import os
from pathlib import Path
import numpy as np
from ase.io import read as aread, write as awrite
import json

#Read from json file
with open(args.template_file) as f:
    runparams = json.loads(f.read())

runtypes = runparams["defect_types"]
run_nums = runparams["run_indices"]

step_size = runparams["step_size"]
Nt = runparams["step_count"]
temperature = runparams["temperature"]
pimd_type = runparams["PIMD_type"]
nbeads = runparams["num_beads"]
template_outprefix = runparams["output_name"]
pdbinput = runparams["pdb_input_name"]
modelname = runparams["MACE_model"]


cwd = Path("./").resolve()
assert cwd.name == "PI-production", f"Wrong directory: {str(cwd)}"
data_dir = cwd.parents[1] /"Data"
templates_dir = cwd / "templates"
model_path = f"/work/e898/shared/waf25/mace-models/{modelname}"

#Set up output directories for PIMD production run

for rt in runtypes:
    for rn in run_nums:
        for T, P in zip(temperature, nbeads):

            # Swap in run parameters to outprefix
            outprefix = template_outprefix.replace("XXXTEMPXXX", f"{T}")
            outprefix = outprefix.replace("XXXNBEADSXXX", f"{P}")

            #Make output directory (if necessary)
            workdir = cwd /  f"out/{rt}-{rn:02d}/{outprefix}"

            print(f"Making directory {str(workdir.absolute())}")

            if not(workdir.exists()):
                workdir.mkdir(parents=True)
                workdir.chmod(0o755)

                #Check that the output directory is linked up
                data_parent = data_dir / f"out/PI-production-out/{rt}-{rn:02d}"
                if not(data_parent.exists()):
                    data_parent.mkdir(parents=True)
                    data_parent.chmod(0o755)

                link_dir = data_parent / f"{outprefix}"

                if not(link_dir.is_symlink()):
                    #Symlink output directory to pair in Data/out/PI-production-out
                    os.symlink(workdir, link_dir, target_is_directory=True)
            else:
                print(f"Directory {str(workdir)} exists")

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
            lammps_inp = templates_dir / "input.lmp"

            #Get ipi input
            ipi_inp = templates_dir / f"{pimd_type}.xml"

            edit_inputs = [lammps_inp, ipi_inp]
            inptext = ['', '']
            for ini, inp in enumerate(edit_inputs):
                with open(inp, "r") as ii:
                    inptext[ini] = ii.read()

                #Swap out placeholders

                #Global (only ipi at this point)
                inptext[ini] = inptext[ini].replace(f"XXXTEMPXXX", f"{T}")
                inptext[ini] = inptext[ini].replace(f"XXXOUTPREFXXX", outprefix)
                inptext[ini] = inptext[ini].replace(f"XXXNSTEPSXXX", f"{Nt}")

                #LAMMPS input file
                inptext[ini] = inptext[ini].replace(f"XXXSTEPSIZEXXX", f"{step_size}")
                inptext[ini] = inptext[ini].replace(f"XXXMODELPATHXXX", str(model_path))

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
                pdbo.write(f"TITLE <{rt}-{rn:02d}>" + r"position{angstrom} cell{angstrom}" + '\n')

                pdbo.writelines(filtered)


            #Save lammps input
            lammps_inp_out = workdir / f"input-{outprefix}.lmp"
            with open(lammps_inp_out, "w") as lio:
                lio.write(inptext[0])

            #Save ipi input
            ipi_inp_out = workdir / f"input-{outprefix}.xml"
            with open(ipi_inp_out, "w") as iio:
                iio.write(inptext[1])
