"""cmdai: which arms of `$6522` the natural runs reach.  `hits` over a long run from each start snapshot, one line of counts per snapshot.

    cd M68000 && .venv/bin/python reversing/powermonger/py/cmdai/census.py [steps]
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
STEPS = int(sys.argv[1]) if len(sys.argv) > 1 else 60_000_000
ADDRS = ["6522", "6564", "6584", "6598", "65aa", "65c0", "65dc", "65f4", "661a", "6624", "6638", "664c", "66a4", "66be", "66e8", "6734", "673e", "668c", "6762", "67b4", "6822", "683e", "6884", "6a3a", "6ac6", "6b2e", "4562", "6b38"]


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
    snaps = sorted((ROOT / "scratchpad/pm121/run").glob("*.snap")) + sorted((ROOT / "scratchpad/pm121").glob("k5_s*.snap"))
    with ThreadPoolExecutor(4) as ex:
        for sn, out in ex.map(one, snaps):
            (WORK / "census" / (sn.stem + ".txt")).write_text(out)
            print(sn.name, flush=True)
