"""140th: which entries of the projectile loop `$596a` hold a live projectile?  For each snapshot, runs `bpc 596a 1` N times with a dump of
the 49 slots of `$4be00` after each, and writes {snapshot: [[hit, [(slot, life, type), ...]], ...]} for the hits with a live slot.
`capture_hits.py <snap> 596a <hit,...> <out>` then makes the callcap corpus (`proj_corpus.sh`).

    cd M68000 && python reversing/powermonger/py/proj_scan.py <out.json> <hits> <snap>...
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[3]))
out, nhit, snaps = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
res = {}
for snap in snaps:
    cmds = []
    for _ in range(nhit):
        cmds += ["bpc 596a 1 3000000", "m 4be00 784"]
    cmds.append("q")
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", snap, "repl", "--disk-a", "scratchpad/powermonger.st"],
                       input="\n".join(cmds) + "\n", capture_output=True, text=True, cwd=ROOT,
                       env=dict(os.environ, ATARI_NOTRACE="1"))
    blocks = re.split(r"(?=^--- breakpoint)", p.stdout + p.stderr, flags=re.M)[1:]
    live = []
    for i, b in enumerate(blocks, 1):
        hexline = [l for l in b.splitlines() if re.fullmatch(r"([0-9a-f]{2} ?)+", l.strip()) and len(l.split()) >= 700]
        if not hexline:
            continue
        r = bytes.fromhex("".join(hexline[0].split()))
        slots = [(s, int.from_bytes(r[16 * s + 14:16 * s + 16], "big", signed=True), r[16 * s + 6])
                 for s in range(49) if r[16 * s + 14:16 * s + 16] != b"\0\0"]
        if slots:
            live.append([i, slots])
    res[snap] = {"hits_seen": len(blocks), "live": live}
    print(snap, len(blocks), "entries,", len(live), "with a live slot", flush=True)
Path(out).write_text(json.dumps(res))
