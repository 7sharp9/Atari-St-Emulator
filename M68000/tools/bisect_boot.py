#!/usr/bin/env python3
"""Sample this project's own emulator's register state (PC/CCR/D0-D7/A0-A7) at a list of step
counts from a fresh cold boot, printing one row per sample. Automates a pattern this project's
debugging repeatedly needed by hand: "run to step N, dump registers, repeat for several N to
bisect where some transition happens" (e.g. finding exactly when the interrupt mask changes, or
when PC first reaches a region of interest) - see [[atari-st-emulator-next-instructions]]'s
twenty-eighth pass, which did this by hand five separate times.

Each sample is a fresh `dotnet run --no-build -- <n> snapshot <tmp>` (ATARI_NOTRACE=1, fast) then
a brief `resume <tmp> repl` issuing `r`/`q` to read registers back - the same two-step dance used
manually throughout this project's history, just batched and parsed. Snapshot files are written to
a temp directory and cleaned up after.

Usage (run from the M68000/ project directory, after `dotnet build`):
    python3 tools/bisect_boot.py 100000 335000 340000 345000 350000 355000 360000
    python3 tools/bisect_boot.py --range 300000 400000 --step 10000
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REG_LINE = re.compile(
    r"D0:(\w+) D1:(\w+) D2:(\w+) D3:(\w+)\n"
    r"D4:(\w+) D5:(\w+) D6:(\w+) D7:(\w+)\n"
    r"A0:(\w+) A1:(\w+) A2:(\w+) A3:(\w+)\n"
    r"A4:(\w+) A5:(\w+) A6:(\w+) A7:(\w+)\n"
    r"USP:(\w+) SSP:(\w+)\n"
    r".*\n"
    r"CCR: (\w+)\n"
    r"PC: (\w+)"
)


def sample(step_count: int, tmp_dir: Path) -> dict:
    snap = tmp_dir / f"bisect_{step_count}.snap"
    env = dict(os.environ, ATARI_NOTRACE="1")
    subprocess.run(
        ["dotnet", "run", "--no-build", "--", str(step_count), "snapshot", str(snap)],
        check=True, capture_output=True, text=True, env=env,
    )
    result = subprocess.run(
        ["dotnet", "run", "--no-build", "--", "resume", str(snap), "repl"],
        input="r\nq\n", capture_output=True, text=True,
    )
    snap.unlink(missing_ok=True)
    m = REG_LINE.search(result.stdout)
    if not m:
        return {"step": step_count, "error": "no register dump found - is the build up to date?"}
    d = dict(zip(
        ["D0","D1","D2","D3","D4","D5","D6","D7","A0","A1","A2","A3","A4","A5","A6","A7","USP","SSP","CCR","PC"],
        m.groups(),
    ))
    d["step"] = step_count
    ipl = (int(d["CCR"], 2) >> 8) & 0x7
    d["IPL"] = ipl
    return d


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("steps", nargs="*", type=int, help="explicit step counts to sample")
    p.add_argument("--range", nargs=2, type=int, metavar=("START", "END"), help="sample a range instead of explicit steps")
    p.add_argument("--step", type=int, default=10000, help="step size for --range (default: 10000)")
    args = p.parse_args()

    steps = list(args.steps)
    if args.range:
        start, end = args.range
        steps += list(range(start, end + 1, args.step))
    if not steps:
        sys.exit("no step counts given - pass explicit steps or --range START END")
    steps = sorted(set(steps))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        print(f"{'step':>10} {'PC':>10} {'CCR':>18} {'IPL':>3} {'D0':>10} {'A0':>10}")
        for s in steps:
            r = sample(s, tmp_dir)
            if "error" in r:
                print(f"{s:>10}  ERROR: {r['error']}")
                continue
            print(f"{r['step']:>10} {r['PC']:>10} {r['CCR']:>18} {r['IPL']:>3} {r['D0']:>10} {r['A0']:>10}")


if __name__ == "__main__":
    main()
