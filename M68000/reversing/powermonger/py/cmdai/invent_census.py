"""145th: how many of the AI's invention orders (`$0e`, posted by the follow-up table `$6762`) reach their arrival `$5fa0`.  `hits` over a long run from
each start snapshot: `$6c48` is the executor's `$0e` handler (one hit per executed order, the group goes to state 9), `$5fa0` is the arrival (mode `$22`
lead), `$5cde` the lord's work order it hands out; `$6c32` (`$0c`) and `$6bea` (`$08`) are the two decisions that replace a state-9 group.

    cd M68000 && .venv/bin/python reversing/powermonger/py/cmdai/invent_census.py [steps]

`PM_CENSUS_GLOB` (space-separated snapshot globs relative to M68000) and `PM_CENSUS_OUT` pick other start snapshots and the output directory; `PM_CENSUS_ADDRS` replaces the address list (any `hits` census over the same snapshots).
"""
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
OUT = ROOT / os.environ.get("PM_CENSUS_OUT", "scratchpad/pm145/inv/census")
STEPS = int(sys.argv[1]) if len(sys.argv) > 1 else 60_000_000
ADDRS = os.environ.get("PM_CENSUS_ADDRS", "6c48 5fa0 5cde 6c32 6bea 661a 6762").split()


def one(sn):
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", str(sn), "repl", "--disk-a", "scratchpad/powermonger.st"],
                       input=f"hits {STEPS} {' '.join(ADDRS)}\nq\n", capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
    out = p.stdout + p.stderr
    (OUT / (sn.stem + ".txt")).write_text(out)
    return sn, {a: int(n) for a, n in re.findall(r"\$0*([0-9a-f]+)\s+(\d+)\s+first", out)}


if __name__ == "__main__":
    pats = os.environ.get("PM_CENSUS_GLOB", "scratchpad/pm143/lands/k*.snap")
    snaps = [sn for g in pats.split() for sn in sorted(ROOT.glob(g))]
    OUT.mkdir(parents=True, exist_ok=True)
    total = dict.fromkeys(ADDRS, 0)
    with ThreadPoolExecutor(12) as ex:
        for sn, c in ex.map(one, snaps):
            print(sn.stem, " ".join(f"{a}={c.get(a, 0)}" for a in ADDRS), flush=True)
            for a in ADDRS:
                total[a] += c.get(a, 0)
    print("TOTAL", " ".join(f"{a}={total[a]}" for a in ADDRS), "over", len(snaps), "snapshots of", STEPS, "steps")
