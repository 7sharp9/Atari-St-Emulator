"""cmdai corpus: natural entries of `$6522` (the commander AI, once per tick) from the 35 land snapshots of pm121.

Writes <WORK>/corpus/<snap>_<hit>.snap/.ram + <snap>.json (tools/capture_hits.py format).

    cd M68000 && .venv/bin/python reversing/powermonger/py/cmdai/capture_corpus.py
"""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
WORK_REL = "scratchpad/pm141/agents/cmdai"          # data (corpus/, g/, gx/, gw/, census/): scratchpad, not committed
WORK = ROOT / WORK_REL
OUT = f"{WORK_REL}/corpus"
HITS = "1,2,4,8,16,32,64,128,256"


def one(sn):
    r = subprocess.run([sys.executable, "tools/capture_hits.py", str(sn.relative_to(ROOT)), "6522", HITS, OUT,
                        "--name", sn.stem, "--max", "20000000"], cwd=ROOT, capture_output=True, text=True)
    return sn.stem, r.returncode, r.stdout.strip().splitlines()[-1:] + r.stderr.strip().splitlines()[-1:]


if __name__ == "__main__":
    snaps = sorted((ROOT / "scratchpad/pm121").glob("k*.snap"))
    snaps += [ROOT / "scratchpad/pm123/win/m1_s0.snap"]
    with ThreadPoolExecutor(4) as ex:
        for res in ex.map(one, snaps):
            print(res, flush=True)
