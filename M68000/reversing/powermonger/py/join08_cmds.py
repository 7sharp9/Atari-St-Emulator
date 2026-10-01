"""join08_cmds.py <snap-in> <outdir> <target x,y> [quota-poke-lord0-field]: writes <outdir>/cmds, a REPL script
that arms order $08 (icon 275,162), clicks the target on the minimap/screen, then snapshots (stage 2 is join08_watch.py).
Run with:  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume <snap> repl --disk-a scratchpad/powermonger.st < cmds
Repo root comes from __file__."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'reversing' / 'powermonger' / 'py'))

HOME = ["mouse move -400 -400", "s 300000", "mouse move 0 0", "s 300000"]
snap_out = sys.argv[2]
tx, ty = map(int, sys.argv[1].split(','))
pokes = sys.argv[3:]          # raw REPL commands with ':' for spaces, applied before the clicks

out = []
out += [p.replace(':', ' ') for p in pokes]
out += HOME
# arm the order icon (275,162)
out += ["mouse move 275 162", "s 300000", "mouse move 0 0", "s 300000",
        "mouse down l", "mouse move 0 0", "s 300000", "mouse up l", "mouse move 0 0", "s 300000",
        "m 57fd4 2"]
# click the target; hits armed before the press (the click is consumed in the settle after down)
out += [f"mouse move {tx-275} {ty-162}", "s 300000", "mouse move 0 0", "s 300000",
        "mouse down l", "mouse move 0 0",
        "hits 400000 6bea 3154 3248 15122 34f2",
        "mouse up l", "mouse move 0 0", "s 300000", "m 57fd4 2",
        "m 51970 2", f"snap {snap_out}/clicked.snap", "q"]
print('\n'.join(out))
