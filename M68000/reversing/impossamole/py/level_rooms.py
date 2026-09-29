"""Print the room graph of the world a snapshot is in (tables at $c028 and $e0aa; README "Rooms").

    uv run python reversing/impossamole/py/level_rooms.py <snap> [--route GOAL_START GOAL_END]

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

def route(start, recs, goal):
    """Shortest exit sequence from the start room to any room whose block range contains `goal` blocks."""
    from collections import deque
    q, seen = deque([(start, [])]), {start}
    while q:
        room, path = q.popleft()
        if room[0] <= goal[0] and goal[1] <= room[1] and room != start:
            return path
        for dr, trig, sb, eb, hx in recs:
            if room[0] <= trig < room[1] and (sb, eb) not in seen:
                seen.add((sb, eb)); q.append(((sb, eb), path + [(room, dr, trig, (sb, eb), hx)]))
    return None


ram = ram_from_snap(Path(sys.argv[1]))
w, start, recs = transitions(ram)
print(f'world {w}: start room blocks {start[0]}..{start[1]} (px {start[0] * 32}..{start[1] * 32}, camera limit ${start[1] * 32 - 256:x})')
for dr, trig, sb, eb, hx in recs:
    inroom = '|'.join(f'{a}..{b}' for a, b in sorted({start} | {(r[2], r[3]) for r in recs}) if a <= trig < b)
    print(f'  {"top " if dr == 0 else "down"} exit at block {trig:3} (col {trig * 4:4}, in {inroom}) -> room {sb}..{eb}, hero block-x {hx}')

if len(sys.argv) > 3 and sys.argv[2] == '--route':
    goal = (int(sys.argv[3]), int(sys.argv[4]))
    path = route(start, recs, goal)
    print(f'route to a room containing blocks {goal[0]}..{goal[1]}:', 'none' if path is None else '')
    for room, dr, trig, dest, hx in path or []:
        print(f'  in {room[0]}..{room[1]}: {"leave through the top" if dr == 0 else "fall through the bottom"} at block {trig} (col {trig * 4}) -> {dest[0]}..{dest[1]}, arrive at block-x {hx}')
