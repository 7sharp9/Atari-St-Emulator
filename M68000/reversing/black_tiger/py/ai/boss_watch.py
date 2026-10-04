#!/usr/bin/env python3
"""Watch a boss: from boss<N>.snap (drive_boss.py) poke the hero next to the boss and sample the boss
records and the P/E shot tables every CHUNK steps.  LABELLED POKES: hero x:y (`w 1f014`), and every
sample the hero's armour `$1f006 := 99` and hits `$1f00e := 99` so the hero survives.
usage: boss_watch.py LEVEL [frames=70] [chunk=60000] [dx=-48]   -> boss/watch<LEVEL>.txt
The hero starts 200 px left of the boss for 8 samples (boss still dormant), then is moved to boss.x+dx."""
import os, subprocess, sys
from btram import *

lvl = int(sys.argv[1]); N = int(sys.argv[2]) if len(sys.argv) > 2 else 70
CH = int(sys.argv[3]) if len(sys.argv) > 3 else 60000
DX = int(sys.argv[4]) if len(sys.argv) > 4 else -48
snap = os.path.join(OUT, "boss", "boss%d.snap" % lvl)
r = load(snap)
bx, by = w(r, 0x1F024), w(r, 0x1F026)
cmds = []
for i in range(N):
    cmds += ["w 1f014 %04x%04x" % ((bx + (-200 if i < 8 else DX)) & 0xFFFF, by & 0xFFFF)] if i in (0, 8) else []
    cmds += ["s %d" % CH, "m 1f020 128", "m 317b8 420", "m 31612 420", "w 1f00c 00050063", "w 1f006 00630000"]
cmds.append("q")
p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", os.path.relpath(snap, ROOT), "repl",
                    "--disk-a", os.path.relpath(os.path.join(WORK, "bt_auto.st"), ROOT)],
                   input="\n".join(cmds) + "\n", capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
lines = [l.strip() for l in p.stdout.splitlines() if l.strip() and all(c in "0123456789abcdef " for c in l.strip())]
out = []
for i in range(N):
    a, pt, et = lines[3 * i:3 * i + 3]
    act = bytes.fromhex(a.replace(" ", "")); P = bytes.fromhex(pt.replace(" ", "")); E = bytes.fromhex(et.replace(" ", ""))
    recs = []
    for k in range(8):
        q = act[16 * k:16 * k + 16]
        if q[0]:
            recs.append("t%d s%d f%d d%d (%d,%d) hp%d st%d" % (q[0], q[1], q[2], q[3], (q[4] << 8) | q[5], (q[6] << 8) | q[7], q[8], q[9]))
    pt_ = [P[14 * k + 1] for k in range(30) if not P[14 * k] & 0x80]
    et_ = [E[14 * k + 1] for k in range(30) if not E[14 * k] & 0x80]
    out.append("%3d | %s | P%s E%s" % (i, " ; ".join(recs), pt_, et_))
open(os.path.join(OUT, "boss", "watch%d.txt" % lvl), "w").write("\n".join(out) + "\n")
print("\n".join(out[:int(os.environ.get("SHOW", "40"))]))
