"""Capture the object pool ($302f6, 18-byte records, count $32a3c) at every arrival at the walker $1fa72.

    uv run python pool_capture.py <snap> <frames> <out.json>

The file also holds the height map $42a58 and the object map $32a58 at frame 0 ('hmap', 'map0') and, per frame,
the object-map bytes that changed since the previous arrival ('mapdiff': [[cell, new byte], ...]).
Each row: the count, the pool bytes (hex), gravity $32a3a, frame counter $32a44, the camera $270ce, the ship
$270b0, the RNG $2706e (8 bytes) and the step counter. The row at frame k is the pool as the walker is about
to run on it (after the previous frame's spawns). Writes only <out.json>.
"""
import json
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon
from vcommon import ROOT, WORK, work
from stclient import StServer

WALK = 0x1fa72
def main():
    snap, n, out = os.path.abspath(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    s = StServer(ROOT)
    rows = []
    try:
        s('load', snapshot=snap)
        s('bp_set', addrs=[WALK])
        rd = lambda a, k: s('read', addr=a, len=k)
        last = None
        hmap = rd(0x42a58, 0x10000); prev = bytes.fromhex(rd(0x32a58, 0x10000)); map0 = prev.hex()
        while len(rows) < n:
            r = s('run', max_steps=3000000)
            if r['reason'] != 'breakpoint':
                print('stopped', r); break
            if r['steps'] < 64 and last == 'bp':
                continue
            last = 'bp'
            cur = bytes.fromhex(rd(0x32a58, 0x10000))
            diff = [[i, cur[i]] for i in range(0x10000) if cur[i] != prev[i]] if cur != prev else []
            prev = cur
            cnt = int(rd(0x32a3c, 2), 16)
            rows.append({'n': cnt, 'pool': rd(0x302f6, 18 * cnt) if cnt else '', 'g': rd(0x32a3a, 2), 'tick': rd(0x32a44, 2),
                         'cam': rd(0x270ce, 6), 'ship': rd(0x270b0, 12), 'rng': rd(0x2706e, 8), 'step': r.get('step'), 'mapdiff': diff})
    finally:
        s.close()
    json.dump({'snap': snap, 'hmap': hmap, 'map0': map0, 'rows': rows}, open(out, 'w'))
    print(len(rows), 'frames; max count', max(r['n'] for r in rows))
main()
