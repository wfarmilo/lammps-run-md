# CL-production

Folder for production runs with classical MD. Subfolders (except `templates/`) contain other production pipelines explain below.

## Sequencing
1) `setup.sh` will create required output folders, and clone necessary LAMMPS inputs.
2) `run.sh` will send off all configured jobs to SLURM, built for ARCHER2 (RIP).

## Input parameters
By default, the parameters which specify which runs create folders for, naming conventions, and input parameters are all located in `templates/production.json`. An example of this is as follows:

```json
{
    "compounded" : true,
    "defect_types" : ["p0m0", "p0m1", "p1m0"],
    "run_indices" : [0, 1, 2, 3, 4],
    "temperature" : [200, 250],
    "step_size" : 8,
    "step_count" : 4000000,
    "output_name" : "XXXOUTPREFXXX",
    "pdb_input_name" : "XXXDFXXX",
    "MACE_model" : "ch2o-dens-inv_swa-1-8.json"
}

```
- **compounded** (*bool*): whether to do the product of every single possible combination of inputs (true) or to run each defect type, run index and temperature pair in serial (false, e.g. Python's zip())
- **defect_types** (*list[str]*): the simulation types to run, named pXmY for a system with X added H+ and Y removed H+.
- **temperature** (*int*): the temperature (K) at which to run our simulations
- **run_indices** (*list[int]*): the run index corresponding to the unique initial condition
- **step_size** (*int*): the number of frames between MD saves (classical MD uses 0.5fs/step).
- **step_count** (*int*): the number of frames to run in total.
- **output_name** (*str*): should always be **XXXOUTPREFXXX**, gets replaced for each individual output in `setup.py`.
- **pdb_input_name** (*str*): name of input pdb file from Data/input-pdb/{name}.pdb. The string **XXXDFXXX** will be replaced at runtime with **defect_type**.
- **MACE_model** (*str*): the name of the symmetrix-extracted MACE model to use, as it is called under the shared mace-models/ directory.
