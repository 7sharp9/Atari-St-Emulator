"""Print the room graph of the world a snapshot is in (tables at $c028 and $e0aa; README "Rooms").

    uv run python reversing/impossamole/py/level_rooms.py <snap>

Room = block range (rooms can overlap: a sub-room reuses part of a larger room's range) [start,end) of the one 1680-column tile map; a block is 32px (4 tile columns).
A trigger fires when the hero leaves the screen through the top (dir 0, state $227f3=2) or bottom
(dir 1, state $227f3=3) with hero block ((x-$20+camera+16)>>5) equal to the trigger block; it loads
room [dest start, dest end) and puts the hero at x=(dest block-x<<5)+$20, y=-16 (bottom exit) or
$c8 (top exit).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from level_map import transitions
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
from pm_export import ram_from_snap

ram = ram_from_snap(Path(sys.argv[1]))
w, start, recs = transitions(ram)
print(f'world {w}: start room blocks {start[0]}..{start[1]} (px {start[0] * 32}..{start[1] * 32}, camera limit ${start[1] * 32 - 256:x})')
for dr, trig, sb, eb, hx in recs:
    inroom = '|'.join(f'{a}..{b}' for a, b in sorted({start} | {(r[2], r[3]) for r in recs}) if a <= trig < b)
    print(f'  {"top " if dr == 0 else "down"} exit at block {trig:3} (col {trig * 4:4}, in {inroom}) -> room {sb}..{eb}, hero block-x {hx}')
