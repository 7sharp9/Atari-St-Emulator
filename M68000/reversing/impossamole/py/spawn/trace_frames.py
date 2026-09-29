"""Frame-synchronised object tracer: one sample per game frame, taken when the per-frame object pass `$00b4de` starts
(after every handler of that frame has run, before positions move).

    ATARI_NOTRACE=1 uv run python trace_frames.py <snap> <frames> <slot,slot,...> [out.json]

Returns/writes, per frame, the fields of each slot (replx.Repl.obj). `trace(r, slots, frames)` is the API used by the
verification scripts. The REPL stops at `$b4de` with `bp b4de`; `s 1` first so the next call does not stop at once.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl


def trace(r, slots, frames, extra=None):
    out = []
    for f in range(frames):
        r.run('s 1', 'bp b4de 200000')
        rec = {}
        for s in slots:
            o = r.obj(s)
            o.pop('raw')
            rec[s] = o
        if extra:
            rec['extra'] = extra(r)
        out.append(rec)
    return out


if __name__ == '__main__':
    snap, frames, slots = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3].split(',')]
    with Repl(snap) as r:
        t = trace(r, slots, frames)
    if len(sys.argv) > 4:
        json.dump(t, open(sys.argv[4], 'w'))
    for i, rec in enumerate(t):
        print(i, ' '.join(f"s{s}:({o['x']},{o['y']}) 82={o['w82']} 84={o['w84']} d={o['b20']}{o['b21']}" for s, o in rec.items() if s != 'extra'))
