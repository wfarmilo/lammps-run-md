"""
This program cleans up duplicated i-pi steps in all my runs, then lists all cleaned up runs in cleaned-restarts.txt 
to avoid double cleaning. Can specify -a, --all to clean all files, or -n, --name to clean specific files

"""

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-a", "--all", action = "store_true", help = "Run for all systems")
parser.add_argument("-u", "--update", action = "store_true", help = "Specifically update for files modified after last clean")
parser.add_argument("-n", "--name", nargs = "*", default = [], help = "File names to specifically re-clean")

args = parser.parse_args()

from pathlib import Path
import time

data_dir = Path("../Data/out/PI-production-out")

assert data_dir.exists()

do_all = args.all
update = args.update
target = args.name

# Read in completed runs, and their mtimes
filein = Path("../Data/cleaned-restarts.txt")
with open(filein, "r") as f:
    filelines = f.readlines()

# Format is mtime then filename 
filenames = []
mtimes = []
for line in filelines:
    mtime, name = line.split()
    filenames.append(name)
    mtimes.append(int(mtime))

# Output lists
filenames_out = []
mtimes_out = []

# Time at which this program was run
verify_time = time.time_ns()

# Glob together all data
for simtype in data_dir.glob("p[0-9]m[0-9]-[0-9][0-9]/"):
    params = simtype.glob("*/")
    for param in params:
        runs = param.glob("*xyz")
        for run in runs:
            # Get mtime (as integer)
            rtime = run.stat().st_mtime_ns

            # Condition under which we do a run (relying on short-circuit here to not break list.index)
            run_str = str(run.absolute())
            condition = (
                do_all or 
                (run_str in target) or 
                (run_str not in filenames) or
                (mtimes[filenames.index(run_str)] < rtime)
            )
            
            if condition:
                # Look for duplicates
                with open(run, "r") as r:
                    lines = enumerate(r)
                    _, line1 = next(lines)
                    Na = int(line1)
                    framelen = Na + 2

                    seen_steps = set()
                    delete_frames = set()
                    for i, line in lines:
                        if (i - 1) % framelen == 0:
                            # Grab the step idx (first thing that comes after the word "Step:")
                            step = line.split("Step:", 1)[1].split()[0]
                            if step in seen_steps:
                                delete_frames.update(range(i-1, i-1 + framelen))
                            else:
                                seen_steps.add(step)

                # If we found duplicates, clean them out
                if len(delete_frames) > 0:

                    # Write clean data to temp file
                    tmp_path = run.with_suffix(run.suffix + '.tmp')
                    with open(run, "r") as r_in, open(tmp_path, "w") as w:
                        lines = enumerate(r_in)
                        for i, line in lines:
                            if i in delete_frames:
                                continue
                            w.write(line)

                    # Map temp file to real name
                    tmp_path.replace(run)

                # Whether anything was changed or not, add file to list with mtime
                filenames_out.append(run_str)
                mtimes_out.append(verify_time)

            else:
                # If we dont need to modify it, preserve the existing mtime
                filenames_out.append(run_str)
                mtimes_out.append(mtimes[filenames.index(run_str)])

            print(f"Found {len(delete_frames) // framelen} in {"/".join(run_str.split("/")[-3:])}")

with open(filein, "w") as f:
    for fn, mt in zip(filenames_out, mtimes_out):
        f.write(f"{mt} {fn}\n")
            