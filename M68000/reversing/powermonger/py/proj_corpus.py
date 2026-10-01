"""140th: the callcap corpus of `$596a` (the projectile loop) from the scans of `proj_scan.py`: per snapshot the entries where a slot
has life 1 (the impact) or 2 (the last flight step), plus every 8th live entry, at most 30; `capture_hits.py` writes the
snapshots under scratchpad/pm140/proj/corpus/<name>/.

    cd M68000 && python reversing/powermonger/py/proj_corpus.py scratchpad/pm140/proj/scan_*.json
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[3]))
for f in sys.argv[1:]:
    for snap, v in json.load(open(f)).items():
        sel = []
        for k, (hit, slots) in enumerate(v["live"]):
            if any(life in (1, 2) for _s, life, _t in slots) or k % 8 == 0:
                sel.append(hit)
        sel = sorted(set(sel))[:30]
        if not sel:
            continue
        name = Path(snap).stem
        subprocess.run([sys.executable, "tools/capture_hits.py", snap, "596a", ",".join(map(str, sel)),
                        f"scratchpad/pm140/proj/corpus/{name}", "--name", name, "--max", "100000000"], cwd=ROOT, check=True)
