"""Frame-by-frame state timeline of one enemy slot, run-length compressed.

    ATARI_NOTRACE=1 uv run python timeline.py <snap> <slot> <frames> [poke ...]

One row per change of (anim pointer, 78, 100, dead, direction bytes, speeds): frame range, x, y range, frame word(s).
`poke` arguments are REPL lines sent before tracing (e.g. `w 1a574 00a00000` to move the hero: labelled pokes only).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl
from trace_frames import trace


def compress(tr, slot):
    rows = []
    for i, t in enumerate(tr):
        o = t[slot]
        key = (o['tw'], o['anim'], o['b78'] if o['b78'] < 3 else 3, int(o['st'] > 0), o['dead'], o['b20'], o['b21'], o['w16'], o['w18'], o['hp'], int(o['inv'] > 0))
        if rows and rows[-1]['key'] == key:
            r = rows[-1]
            r['end'] = i
            r['xs'].append(o['x']); r['ys'].append(o['y']); r['frames'].append(o['frame'])
        else:
            rows.append(dict(key=key, start=i, end=i, xs=[o['x']], ys=[o['y']], frames=[o['frame']]))
    return rows


def show(rows):
    for r in rows:
        tw, anim, b78, st, dead, d20, d21, v16, v18, hp, inv = r['key']
        fr = []
        for f in r['frames']:
            if not fr or fr[-1] != f:
                fr.append(f)
        fr_s = ','.join(map(str, fr[:12])) + ('...' if len(fr) > 12 else '')
        print(f"f{r['start']:3d}-{r['end']:3d} tw{tw} anim ${anim:05x} 78={b78 if b78 < 3 else '3+'} frz={st} dead={dead} dir={d20}{d21} v=({v16},{v18}) hp={hp} inv={inv} "
              f"x {r['xs'][0]}..{r['xs'][-1]} y {min(r['ys'])}..{max(r['ys'])} frames [{fr_s}]")


if __name__ == '__main__':
    snap, slot, frames = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    with Repl(snap) as r:
        if len(sys.argv) > 4:
            r.run(*sys.argv[4:])
        tr = trace(r, [slot], frames)
    show(compress(tr, slot))
