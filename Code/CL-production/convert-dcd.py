"""
One-off conversion of CL-production run directories from DCD trajectories to the
append-friendly LAMMPS custom dump (.lammpstrj, columns: id type element xu yu zu),
so that run.sh can continue every run by appending to a single trajectory file.

Standalone: imports nothing from this repo and modifies no tracked file. Per run
directory (<root>/pXmY-ZZ/prod-TNNN/) it:

  1. Reads traj-prod-TNNN.dcd (unwrapped coordinates, atoms in id order) and checks
     the header against the file size.
  2. Reads ids/types/box/elements from initconf.data.
  3. Picks the unique final-prod-TNNN.<R>.restart whose step R matches the DCD's
     last frame (lastframe <= R < lastframe + stride).
  4. Relabels timesteps so the trajectory starts at 0: new step = old step - ISTART,
     restart step R_new = R - ISTART. Runs whose DCD already starts at 0 are unchanged.
     Frames at step >= R_new are dropped (LAMMPS re-dumps step R_new on continuation
     whenever R_new is a multiple of the stride).
  5. Writes traj-prod-TNNN.lammpstrj in the same layout LAMMPS writes, with %g floats
     (LAMMPS's default), so later appended frames are indistinguishable.
  6. Writes final-prod-TNNN.<R_new>.restart by byte-patching only the NTIMESTEP,
     ATIMESTEP and ATIME header fields of the source restart. Everything else
     (thermostat state, velocities, image flags) stays byte-identical.
  7. Rewrites the dump/dump_modify lines of this directory's input-prod-TNNN.lmp and
     input-restart-prod-TNNN.lmp (the files run.sh submits) to the lammpstrj dump.
  8. Deletes every other final-*.restart, the chkpt-*.restart files, and leftover
     reset-timestep-* files. The .dcd is kept.

Defaults to a dry run (prints what would happen, writes nothing). Pass --apply to act.
Refuses to overwrite an existing .lammpstrj (it may already hold continued frames)
unless --force is given.

Usage:
    python convert-dcd.py ROOT_OR_RUNDIR [...] [--apply] [--force]
"""

import argparse
import re
import struct
import sys
from pathlib import Path

import numpy as np

CHUNK = 2000  # frames formatted per write

# LAMMPS restart header flags (src/lmprestart.h)
NTIMESTEP_FLAG = 5
TIMESTEP_FLAG = 50
ATIME_FLAG = 70
ATIMESTEP_FLAG = 71
RESTART_MAGIC = b"LammpS RestartT\x00"
RESTART_HEADER_SCAN = 4096  # all header fields live well inside this


############################## DCD ##############################

def read_dcd_header(path):
    """Return (nset, istart, nsavc, has_cell, natom, header_bytes) of a LAMMPS DCD."""
    with open(path, "rb") as f:
        n, = struct.unpack("<i", f.read(4))
        body = f.read(n)
        n_end, = struct.unpack("<i", f.read(4))
        if n != 84 or n_end != 84 or body[:4] != b"CORD":
            raise ValueError(f"{path}: not a little-endian CHARMM/LAMMPS DCD")
        icntrl = struct.unpack("<20i", body[4:84])
        nset, istart, nsavc = icntrl[0], icntrl[1], icntrl[2]
        has_cell = icntrl[10] == 1

        n, = struct.unpack("<i", f.read(4))   # title record
        f.seek(n + 4, 1)

        n, natom, n_end = struct.unpack("<3i", f.read(12))
        if n != 4 or n_end != 4:
            raise ValueError(f"{path}: malformed natom record")
        return nset, istart, nsavc, has_cell, natom, f.tell()


def dcd_frames(path):
    """Memory-map the DCD frames; returns (header dict, structured memmap)."""
    nset, istart, nsavc, has_cell, natom, hdr = read_dcd_header(path)

    fields = []
    if has_cell:
        fields += [("c0", "<i4"), ("cell", "<f8", 6), ("c1", "<i4")]
    for ax in "xyz":
        fields += [(f"{ax}0", "<i4"), (ax, "<f4", natom), (f"{ax}1", "<i4")]
    dtype = np.dtype(fields)

    size = path.stat().st_size
    if size != hdr + nset * dtype.itemsize:
        raise ValueError(f"{path}: size {size} != header {hdr} + {nset} frames x "
                         f"{dtype.itemsize} B (truncated or not a single-writer DCD)")

    frames = np.memmap(path, dtype=dtype, mode="r", offset=hdr, shape=(nset,))

    # Fortran record markers must be consistent in every frame
    if has_cell and not ((frames["c0"] == 48).all() and (frames["c1"] == 48).all()):
        raise ValueError(f"{path}: bad unit-cell record markers")
    for ax in "xyz":
        if not ((frames[f"{ax}0"] == 4 * natom).all() and (frames[f"{ax}1"] == 4 * natom).all()):
            raise ValueError(f"{path}: bad {ax} record markers")

    head = dict(nset=nset, istart=istart, nsavc=nsavc, has_cell=has_cell, natom=natom)
    return head, frames


########################## initconf.data ##########################

def read_lammps_data(path):
    """Return (box [(lo, hi)]*3, ids, types, {type: element}) from an atomic-style data file."""
    lines = path.read_text().splitlines()

    box = {}
    for line in lines:
        m = re.match(r"\s*(\S+)\s+(\S+)\s+([xyz])lo\s+[xyz]hi", line)
        if m:
            box[m.group(3)] = (float(m.group(1)), float(m.group(2)))
        if re.search(r"\bxy\s+xz\s+yz\b", line):
            raise ValueError(f"{path}: triclinic box not supported")
    if set(box) != {"x", "y", "z"}:
        raise ValueError(f"{path}: missing box bounds")

    def section(name):
        start = next(i for i, l in enumerate(lines) if l.strip().startswith(name))
        out = []
        for l in lines[start + 1:]:
            if not l.strip():
                if out:
                    break
                continue
            out.append(l)
        return out

    elements = {}
    for l in section("Masses"):
        if "#" not in l:
            raise ValueError(f"{path}: Masses line without '# Element' comment: {l!r}")
        typ, el = int(l.split()[0]), l.split("#", 1)[1].strip()
        elements[typ] = el

    atoms = np.array([l.split()[:2] for l in section("Atoms")], dtype=int)
    order = np.argsort(atoms[:, 0])
    ids, types = atoms[order, 0], atoms[order, 1]

    return [box[a] for a in "xyz"], ids, types, elements


############################ restart ############################

def find_field(buf, flag, fmt, value=None, tol=None):
    """Offsets in buf where int32 `flag` is followed by a `fmt` value (optionally == value)."""
    hits = []
    marker = struct.pack("<i", flag)
    width = struct.calcsize(fmt)
    for m in re.finditer(re.escape(marker), buf[:RESTART_HEADER_SCAN]):
        pos = m.start() + 4
        v, = struct.unpack(fmt, buf[pos:pos + width])
        if value is None:
            hits.append((pos, v))
        elif tol is None and v == value:
            hits.append((pos, v))
        elif tol is not None and abs(v - value) <= tol:
            hits.append((pos, v))
    return hits


def patch_restart(src, step_old, step_new):
    """Return the bytes of `src` with NTIMESTEP/ATIMESTEP/ATIME moved from step_old to step_new."""
    buf = bytearray(src.read_bytes())
    if not buf.startswith(RESTART_MAGIC):
        raise ValueError(f"{src}: not a LAMMPS restart file")

    nts = find_field(buf, NTIMESTEP_FLAG, "<q", step_old)
    ats = find_field(buf, ATIMESTEP_FLAG, "<q", step_old)
    if len(nts) != 1 or len(ats) != 1:
        raise ValueError(f"{src}: expected exactly one NTIMESTEP and ATIMESTEP == {step_old}, "
                         f"found {len(nts)} and {len(ats)}")
    nts_pos, ats_pos = nts[0][0], ats[0][0]

    # ATIME is written straight after ATIMESTEP
    atime_flag, atime = struct.unpack("<id", buf[ats_pos + 8:ats_pos + 20])
    if atime_flag != ATIME_FLAG:
        raise ValueError(f"{src}: ATIME does not follow ATIMESTEP")
    atime_pos = ats_pos + 12

    # Times are step*dt throughout these runs; check that against the stored timestep size
    dt = atime / step_old
    if len(find_field(buf, TIMESTEP_FLAG, "<d", dt, tol=1e-12)) != 1:
        raise ValueError(f"{src}: ATIME={atime} is not step*dt for the stored dt")

    buf[nts_pos:nts_pos + 8] = struct.pack("<q", step_new)
    buf[ats_pos:ats_pos + 8] = struct.pack("<q", step_new)
    buf[atime_pos:atime_pos + 8] = struct.pack("<d", step_new * dt)
    return bytes(buf)


########################## input files ##########################

def patch_input(path, prefix, stride, elements, append):
    """Return text of `path` with its DUMP1 dump/dump_modify lines replaced by the lammpstrj dump."""
    dump_line = f"dump DUMP1 all custom {stride} traj-{prefix}.lammpstrj id type element xu yu zu"
    modify_line = f"dump_modify DUMP1 element {elements} sort id" + (" append yes" if append else "")

    out, saw_dump, saw_modify = [], False, False
    for line in path.read_text().splitlines(keepends=True):
        tokens = line.split()
        if tokens[:2] == ["dump", "DUMP1"]:
            if saw_dump:
                raise ValueError(f"{path}: more than one 'dump DUMP1' line")
            if int(tokens[4]) != stride:
                raise ValueError(f"{path}: dump stride {tokens[4]} != DCD stride {stride}")
            out.append(dump_line + "\n")
            saw_dump = True
        elif tokens[:2] == ["dump_modify", "DUMP1"]:
            if not saw_modify:
                out.append(modify_line + "\n")
                saw_modify = True
            # further dump_modify DUMP1 lines are folded into the one above
        else:
            out.append(line)

    if not saw_dump:
        raise ValueError(f"{path}: no 'dump DUMP1' line")
    if not saw_modify:
        idx = next(i for i, l in enumerate(out) if l == dump_line + "\n")
        out.insert(idx + 1, modify_line + "\n")
    return "".join(out)


########################## trajectory ##########################

def write_lammpstrj(path, frames, steps, box, ids, types, elements):
    """Write frames[:len(steps)] in LAMMPS dump custom layout (id type element xu yu zu)."""
    natom = len(ids)
    header_tail = (
        "ITEM: NUMBER OF ATOMS\n"
        f"{natom}\n"
        "ITEM: BOX BOUNDS pp pp pp\n"
        + "".join(f"{lo:.16e} {hi:.16e}\n" for lo, hi in box)
        + "ITEM: ATOMS id type element xu yu zu\n"
    )
    atom_fmt = "".join(f"{i} {t} {elements[t]} %g %g %g\n" for i, t in zip(ids, types))

    with open(path, "w") as f:
        for c0 in range(0, len(steps), CHUNK):
            c1 = min(c0 + CHUNK, len(steps))
            chunk = frames[c0:c1]
            xyz = np.stack([chunk["x"], chunk["y"], chunk["z"]], axis=-1).astype(np.float64)
            xyz = xyz.reshape(c1 - c0, 3 * natom)
            f.write("".join(
                f"ITEM: TIMESTEP\n{steps[c0 + k]}\n" + header_tail + atom_fmt % tuple(row)
                for k, row in enumerate(xyz.tolist())
            ))


############################ driver ############################

def convert(rundir, apply, force):
    prefix = rundir.name                          # prod-TNNN
    dcd = rundir / f"traj-{prefix}.dcd"
    traj = rundir / f"traj-{prefix}.lammpstrj"
    data = rundir / "initconf.data"
    inputs = {rundir / f"input-{prefix}.lmp": False,
              rundir / f"input-restart-{prefix}.lmp": True}   # path: append?

    # 1-2. Read and cross-check DCD + data file
    head, frames = dcd_frames(dcd)
    nset, istart, nsavc, natom = head["nset"], head["istart"], head["nsavc"], head["natom"]
    box, ids, types, elements = read_lammps_data(data)

    if len(ids) != natom or not np.array_equal(ids, np.arange(1, natom + 1)):
        raise ValueError(f"{data}: ids are not 1..{natom}")
    if sorted(elements) != list(range(1, len(elements) + 1)) or set(types) - set(elements):
        raise ValueError(f"{data}: atom types {sorted(set(types))} vs Masses {elements}")
    if head["has_cell"]:
        lengths = frames["cell"][0][[0, 2, 5]]
        expected = [hi - lo for lo, hi in box]
        if not np.allclose(lengths, expected, atol=1e-6):
            raise ValueError(f"{dcd}: cell {lengths} != data box {expected}")

    # 3. Source restart matching the DCD's last frame
    last_abs = istart + (nset - 1) * nsavc
    finals = {}
    for p in rundir.glob(f"final-{prefix}.*.restart"):
        m = re.fullmatch(rf"final-{re.escape(prefix)}\.(\d+)\.restart", p.name)
        if m:
            finals[p] = int(m.group(1))
    matches = [p for p, r in finals.items() if last_abs <= r < last_abs + nsavc]
    if len(matches) != 1:
        raise ValueError(f"{rundir}: need exactly one final restart with step in "
                         f"[{last_abs}, {last_abs + nsavc}), found "
                         f"{sorted(finals.values())}")
    src = matches[0]
    R = finals[src]

    # 4. Relabel
    R_new = R - istart
    steps = np.arange(nset, dtype=np.int64) * nsavc
    steps = steps[steps < R_new]
    restart_out = rundir / f"final-{prefix}.{R_new}.restart"

    # Validate everything that will be written before writing anything
    if traj.exists() and not force:
        raise ValueError(f"{traj} already exists (may hold continued frames); use --force")
    restart_bytes = patch_restart(src, R, R_new) if R_new != R else None
    el_str = " ".join(elements[t] for t in sorted(elements))
    input_texts = {p: patch_input(p, prefix, nsavc, el_str, app) for p, app in inputs.items()}

    # restart_out itself is kept (case A) or overwritten (case B), never deleted
    deletions = sorted(
        [p for p in finals if p != restart_out]
        + list(rundir.glob(f"chkpt-{prefix}.*.restart"))
        + list(rundir.glob("reset-timestep-*"))
    )

    print(f"{rundir}: N={natom} DCD steps {istart}..{last_abs} ({nset} frames) -> "
          f"lammpstrj steps 0..{steps[-1]} ({len(steps)} frames); "
          f"restart {src.name} -> {restart_out.name}"
          + ("" if restart_bytes else " (unchanged)"))
    print(f"    delete: {', '.join(p.name for p in deletions) or 'nothing'}")

    if not apply:
        return

    # 5. Trajectory
    tmp = traj.with_name(traj.name + ".tmp")
    write_lammpstrj(tmp, frames, steps, box, ids, types, elements)
    tmp.replace(traj)

    # 6. Restart
    if restart_bytes is not None:
        tmp = restart_out.with_name(restart_out.name + ".tmp")
        tmp.write_bytes(restart_bytes)
        tmp.replace(restart_out)

    # 7. Inputs run.sh submits
    for p, text in input_texts.items():
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(text)
        tmp.replace(p)

    # 8. Remove every restart that no longer matches the trajectory
    for p in deletions:
        p.unlink()

    print("    done")


def find_rundirs(path):
    path = Path(path)
    if any(path.glob("traj-*.dcd")):
        return [path]
    return sorted(d for d in path.glob("p*m*-*/prod-T*") if d.is_dir())


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+",
                        help="Run directories, or roots containing pXmY-ZZ/prod-TNNN/")
    parser.add_argument("--apply", action="store_true", help="Actually convert (default: dry run)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite an existing .lammpstrj")
    args = parser.parse_args()

    rundirs = [d for p in args.paths for d in find_rundirs(p)]
    if not rundirs:
        sys.exit("No run directories found")

    failed = []
    for d in rundirs:
        try:
            convert(d, args.apply, args.force)
        except (OSError, ValueError, StopIteration) as e:
            print(f"{d}: FAILED: {e}")
            failed.append(d)

    print(f"\n{len(rundirs) - len(failed)}/{len(rundirs)} directories "
          f"{'converted' if args.apply else 'OK (dry run)'}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
