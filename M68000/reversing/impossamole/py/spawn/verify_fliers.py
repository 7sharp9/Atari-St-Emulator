"""Live proof of the flier flight paths (README "Spawn types", item b).

    ATARI_NOTRACE=1 uv run python verify_fliers.py [frames]

For each live flier below the frame-synchronised tracer (`trace_frames.py`, one sample per game frame at `$b4de`) is
compared with the reconstruction in `flier_paths.py`: per frame, the next position must equal the current position plus
or minus the speeds by the direction bits, and the frame counter / script indices must follow the transcription. Prints
matched/checked per object. Nothing is poked; the objects run under the game's own loop (health is not needed: the
snapshots are only stepped, no hero input). Camera scroll would shift x, so snapshots where the camera is still are used.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl, ROOT
from trace_frames import trace
import struct
import flier_paths as fp
from tiles import ram_from_snap
from pathlib import Path

CASES = [  # snapshot, slot, type
    ('scratchpad/impossamole/pass99/warp_up112.snap', 7, 125),
    ('scratchpad/impossamole/gameplay_explore/pass84_t2_5M.snap', 9, 123),
    ('scratchpad/impossamole/gameplay_explore/pass84_t2_5M.snap', 7, 124),
    ('scratchpad/impossamole/agents/hop4/room299_poked.snap', 7, 116),
    ('scratchpad/impossamole/pass99/cyc2.snap', 9, 117),
    ('scratchpad/impossamole/pass99/cyc2.snap', 11, 117),
]


def cam(rec):
    return struct.unpack('>H', rec['extra'])[0]


def live_pairs(tr, slot):
    """Consecutive samples while the slot stays occupied (a despawned object leaves stale bytes behind)."""
    for a, b in zip(tr, tr[1:]):
        if a[slot]['tw'] and b[slot]['tw']:
            yield a, b


def check_pingpong(tr, slot, d):
    ok = n = 0
    for a, b in live_pairs(tr, slot):
        o, p = a[slot], b[slot]
        sc = cam(b) - cam(a)          # camera scroll shifts every object's x by minus the camera delta
        vx, vy = d['vx'], d['vy']
        ex = o['x'] + (vx if o['b20'] & 1 else -vx) - sc
        ey = o['y'] + (vy if o['b21'] & 1 else -vy)
        n += 1
        ok += (p['x'], p['y']) == (ex, ey)
        # counter and flip: the next sample's 82 is o.82+1, or 0 on the period, and both direction bits flip on the wrap
        n += 1
        wrap = o['w82'] + 1 == d['period']
        ok += p['w82'] == (0 if wrap else o['w82'] + 1) and ((p['b20'], p['b21']) == ((o['b20'] ^ 1, o['b21'] ^ 1) if wrap else (o['b20'], o['b21'])))
    return ok, n


def check_script(ram, tr, slot, typ):
    d = fp.describe(ram, typ)
    sp, dp = fp.L(ram, d['entry2']), fp.L(ram, d['entry2'] + 4)
    s0 = tr[0][slot]
    s = fp.Script(ram, sp, dp, s0['b20'], s0['b21'])
    s.i82, s.i84, s.b79, s.b80, s.v16, s.v18 = s0['w82'], s0['w84'], s0['b79'], s0['b80'], s0['w16'], s0['w18']
    ok = n = 0
    for a, b in live_pairs(tr, slot):
        o, p = a[slot], b[slot]
        sc = cam(b) - cam(a)
        ex = o['x'] + (o['w16'] if o['b20'] & 1 else -o['w16']) - sc
        ey = o['y'] + (o['w18'] if o['b21'] & 1 else -o['w18'])
        n += 1
        ok += (p['x'], p['y']) == (ex, ey)
        s.step()
        n += 1
        ok += (s.i82, s.i84, s.v16, s.v18, s.d20, s.d21) == (p['w82'], p['w84'], p['w16'], p['w18'], p['b20'], p['b21'])
    return ok, n


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 210
    for snap, slot, typ in CASES:
        ram = ram_from_snap(Path(os.path.join(ROOT, snap)))
        d = fp.describe(ram, typ)
        with Repl(snap) as r:
            live_type = r.obj(slot)
            tr = trace(r, [slot], frames, extra=lambda r: r.mem(0x227b6, 2))
        if d['handler'] == 0x142be:
            ok, n = check_pingpong(tr, slot, d)
        else:
            ok, n = check_script(ram, tr, slot, typ)
        xs = [t[slot]['x'] for t in tr]
        ys = [t[slot]['y'] for t in tr]
        print(f"type {typ} {snap.split('/')[-1]} slot {slot}: {ok}/{n} per-frame checks match over {frames} frames; "
              f"x {min(xs)}..{max(xs)} y {min(ys)}..{max(ys)}", flush=True)


if __name__ == '__main__':
    main()
