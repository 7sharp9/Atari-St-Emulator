"""cmdai: which arms of `$6522` the natural runs reach.  `hits` over a long run from each start snapshot, one line of counts per snapshot.

    cd M68000 && .venv/bin/python reversing/powermonger/py/cmdai/census.py [steps]

`PM_CENSUS_GLOB` (space-separated snapshot globs relative to M68000) and `PM_CENSUS_OUT` (output directory) pick other start snapshots, for
example the Play Random Land lands (`runland.sh` output of `PAGES0=1` builds); the totals over all snapshots are printed at the end.
"""
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
WORK_REL = "scratchpad/pm141/agents/cmdai"          # data (corpus/, g/, gx/, gw/, census/): scratchpad, not committed
WORK = ROOT / WORK_REL
OUT = ROOT / os.environ["PM_CENSUS_OUT"] if os.environ.get("PM_CENSUS_OUT") else WORK / "census"
STEPS = int(sys.argv[1]) if len(sys.argv) > 1 else 60_000_000
ADDRS = ["6522", "6564", "6584", "6598", "65aa", "65c0", "65dc", "65f4", "661a", "6624", "6638", "664c", "66a4", "66be", "66e8", "6734", "673e", "668c", "6762", "67b4", "6822", "683e", "6884", "6a3a", "6ac6", "6b2e", "4562", "6b38",
         "3154", "3248", "38ce", "6128", "5fa0"]      # the order subroutines that no click reaches (strategy.md "The order senders")


def one(sn):
    cmds = f"hits {STEPS} {' '.join(ADDRS)}\nq\n"
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", str(sn), "repl", "--disk-a", "scratchpad/powermonger.st"],
                       input=cmds, capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
    out = p.stdout + p.stderr
    cnt = {}
    for a, n in re.findall(r"\$0*([0-9a-f]+):?\s+(\d+)\s", out):
        cnt.setdefault(a, int(n))
    return sn, out


if __name__ == "__main__":
    pats = os.environ.get("PM_CENSUS_GLOB")
    snaps = ([sn for g in pats.split() for sn in sorted(ROOT.glob(g))] if pats else
             sorted((ROOT / "scratchpad/pm121/run").glob("*.snap")) + sorted((ROOT / "scratchpad/pm121").glob("k5_s*.snap")))
    OUT.mkdir(parents=True, exist_ok=True)
    total = {}
    with ThreadPoolExecutor(4) as ex:
        for sn, out in ex.map(one, snaps):
            (OUT / (sn.stem + ".txt")).write_text(out)
            for a, n in re.findall(r"\$0*([0-9a-f]+):?\s+(\d+)\s", out):
                total[a] = total.get(a, 0) + int(n)
            print(sn.name, flush=True)
    print(f"totals over {len(snaps)} snapshots of {STEPS} steps:")
    for a in ADDRS:
        print(f"  ${a}: {total.get(a, 0)}")
