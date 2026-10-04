"""Level-skip drive: from play_start.snap (level 1 just started) arm the built-in level-skip
(joystick-1 state $85 held while the Home key $47 is read, then Return $1c) and step through the
levels, snapshotting each one and logging the GEMDOS Fopen/Fread calls.

LABELLED POKE-FREE: only keyboard/joystick input, no memory pokes.
usage: drive_levels.py [nskips=7] [wait=6000000]
writes $OUT/lvl<k>.snap / .png and $OUT/logs/drive_levels.log
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from btcommon import *
n = int(sys.argv[1]) if len(sys.argv) > 1 else 7
wait = int(sys.argv[2]) if len(sys.argv) > 2 else 6000000
sc = ["kbd ff 85", "s 100000", "kbd 47", "s 200000", "kbd c7", "s 100000", "kbd ff 00", "s 100000"]
for k in range(1, n + 1):
    sc += ["kbd 1c", "s 100000", "kbd 9c", f"s {wait}", "m 17846 2", f"snap {OUT}/lvl{k}.snap"]
sc.append("quit")
os.makedirs(OUT + "/logs", exist_ok=True)
out = run_repl(os.path.join(WORK, "play_start.snap"), "\n".join(sc) + "\n",
               {"ATARI_TRACE_GEMDOS": "1", "ATARI_TRACE_OS": "1"}, OUT + "/logs/drive_levels.log")
for l in out.splitlines():
    if "Fopen" in l or "Fread" in l or l[:3] in ("00 ",) or "snapshot" in l.lower():
        print(l[:130])
