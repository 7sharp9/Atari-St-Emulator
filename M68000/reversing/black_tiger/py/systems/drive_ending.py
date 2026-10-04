"""Ending drive: from boss7_fight.snap (level index 7, boss active, $1eeb8=1) empty the boss slot so the level-end test
at $c642 (`$1eeb8 != 0` and `$1f020` type byte == 0) passes, then run the real code: $cc80 death-free wipe, level==7 -> $c718:
`bt5` is read to $201cc ($1504 bytes), four text screens, level := 0, $caee reloads btspr behind the "Please insert Disk A"
prompt (wait for a key), then the attract loop.

LABELLED POKE: `w 1f020 00000000` (clears the type byte, +1..+3 of the boss record) = "boss killed".
Requires drive_boss.py to have run.   usage: drive_ending.py   -> $OUT/boss/end1/end2/endprompt/endafter .snap/.png
Step counts after the poke: end1 +3M, end2 +9M, endprompt +21M, key SPACE ($39/$b9) + 3M -> endafter.
"""
import os, re, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from btcommon import *
B = f"{OUT}/boss"
sc = ["w 1f020 00000000", "s 3000000", f"snap {B}/end1.snap", "s 6000000", f"snap {B}/end2.snap", "s 12000000", f"snap {B}/endprompt.snap",
      "m 17846 2", "kbd 39", "s 100000", "kbd b9", "s 3000000", f"snap {B}/endafter.snap", "m 17846 2", "quit"]
out = run_repl(f"{B}/boss7_fight.snap", "\n".join(sc) + "\n", {"ATARI_TRACE_GEMDOS": "1", "ATARI_TRACE_OS": "1"}, B + "/end_drive.log")
print("\n".join(l[:110] for l in out.splitlines() if re.search(r'Fopen|Fread|Bconin|^00 ', l)))
for n in ("end1", "end2", "endprompt", "endafter"):
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "snap_render.py"), f"{B}/{n}.snap", f"{B}/{n}.png"], capture_output=True)
