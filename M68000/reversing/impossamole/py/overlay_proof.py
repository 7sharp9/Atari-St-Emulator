"""overlay_proof.py: do the `[overlay]` boxes of layout.toml sit on the sprites? Measured per slot, with a negative control.

    uv run python reversing/impossamole/py/overlay_proof.py [tag ...]       # from M68000/; default: all three snapshots

For each snapshot, on one `stserver` through tools/stdrive.py:
  1. run to $b26c (`jsr $bafc`, the first of the two sprite passes of the gameplay loop $b1b6, `$bafc` for type 3 in
     slots 7-11 and `$bada` for types 1 and 2, after every logic and background routine of the frame) and fork there;
  2. control arm: run to $b27e (after `jsr $1abb2`, which flips the shifter base to the buffer just drawn), save
     `<tag>_ctrl.snap`; the overlay's boxes are computed from this snapshot, whose live screen is the frame its slot
     fields were drawn from;
  3. per live slot i: restore the fork, poke slot i's type word 0(A0) to 0 (every draw stub, $1b25a, $1b3ec and $bafc's
     test, skips type 0), run to $b27e, save. The two arms differ only in whether slot i was drawn, so the pixels that
     differ between the two rendered screens are slot i's visible sprite pixels: its true on-screen position.
Per slot it reports the predicted box (overlay.py), the measured box (bounding box of the changed pixels), the offset
(how far the measured box sticks out of the predicted one, 0,0 when inside), and a frame fit: the slot's frame (6(A0)
into bank 1 or 2, graphics.md "Sprites", decoded by sprites.py, in the live palette) drawn at the predicted (x, y),
`at 0` the share of changed pixels where it has an opaque pixel of the colour the screen shows, and `best` the shift
(-24..24 px each way) that explains the most (0,0 when the box is right). The box offset alone is weak (a sprite with
transparent margins stays inside a box shifted by a few pixels); the fit is the test.
Negative controls, same arms: the schema's layers with camera_x = w[$227b6] (the level scroll counter, the plausible
wrong reading) and with origin_x = +4.
Output under scratchpad/insights/overlay/proof/: <tag>_ctrl.snap, <tag>_slot<i>.snap, the stdrive journals, report.txt.
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import layout            # noqa: E402
import overlay           # noqa: E402
import snap_render       # noqa: E402
import stdrive as sd     # noqa: E402
from gfxview import load_ram, load_video_regs  # noqa: E402
from sprites import frame_rows  # noqa: E402

DISK = os.path.join(ROOT, 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st')
SNAPS = {
    'boss_room': 'scratchpad/impossamole/pass99/boss_room.snap',
    'cyc5': 'scratchpad/impossamole/pass99/cyc5.snap',
    'room299': 'scratchpad/impossamole/agents/hop3/room299.snap',
}
LAYOUT = os.path.join(ROOT, 'reversing/impossamole/layout.toml')
OUT = os.path.join(ROOT, 'scratchpad/insights/overlay/proof')
SPRITE_PASS, AFTER_FLIP = 0xb26c, 0xb27e
SLOT0, STRIDE = 0x1a2ea, 0x6c
SHIFT = 24


def screen(snap):
    p = snap + '.png'
    if os.path.exists(p):
        os.remove(p)
    snap_render.render(snap, p)
    return np.asarray(Image.open(p).convert('RGB')).astype(np.int16)


def bbox(mask):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def outside(pb, mb):
    """How far the measured box (x0,y0,x1,y1 inclusive) sticks out of the predicted one, per axis; 0 when inside."""
    def ax(p0, p1, m0, m1):
        return m0 - p0 if m0 < p0 else m1 - p1 if m1 > p1 else 0
    return ax(pb[0], pb[2], mb[0], mb[2]), ax(pb[1], pb[3], mb[1], mb[3])


def frame_pixels(ram, pal, slot_addr, x, y, h):
    """{(screen x, screen y): rgb} of the slot's frame's opaque pixels drawn at (x, y), first h rows."""
    typ = min(int.from_bytes(ram[slot_addr:slot_addr + 2], 'big'), 2)     # type 3 draws through the bank-2 body $1b3f8
    fr = int.from_bytes(ram[slot_addr + 6:slot_addr + 8], 'big')
    pix = {(x + dx, y + dy): pal[v] for dy, row in enumerate(frame_rows(ram, typ, fr)[:h]) for dx, v in enumerate(row) if v}
    return fr, pix


def fit(changed, img, pix):
    """A changed pixel is explained at shift (dx, dy) when the frame drawn at the predicted position moved by (dx, dy)
    has an opaque pixel there of the colour the control screen shows. Returns (share explained at shift 0, best shift,
    share at the best shift); ties go to the smaller shift."""
    cy, cx = np.nonzero(changed)
    pts = [(int(a), int(b), tuple(int(c) for c in img[b, a])) for a, b in zip(cx, cy)]
    if not pts:
        return None, None, None

    def score(dx, dy):
        return sum(pix.get((a - dx, b - dy)) == c for a, b, c in pts)
    best = max(((score(dx, dy), -(abs(dx) + abs(dy)), (dx, dy)) for dy in range(-SHIFT, SHIFT + 1)
                for dx in range(-SHIFT, SHIFT + 1)))
    return score(0, 0) / len(pts), best[2], best[0] / len(pts)


def control_layers(layers, kind):
    out = [dict(l) for l in layers]
    for l in out:
        if kind == 'camera':
            l['camera_x'] = layout._Expr('w[0x227b6]', {})
        else:
            l['origin_x'] = l['origin_x'] + 4
    return out


def run_tag(tag, L, layers, rep):
    snap = os.path.join(ROOT, SNAPS[tag])
    d = sd.Drive(ROOT, journal=os.path.join(OUT, f'{tag}.jsonl'), period=24000)
    try:
        d.load(snap, DISK)
        r = d.run(400_000, until_pc=SPRITE_PASS)
        assert r['reason'] == 'until', r
        fork = d.fork()
        before = d.read(SLOT0, 20 * STRIDE)
        r = d.run(400_000, until_pc=AFTER_FLIP)
        assert r['reason'] == 'until', r
        ctrl = d.save(os.path.join(OUT, f'{tag}_ctrl.snap'))
        ram, _ = load_ram(ctrl)
        moved = [i for i in range(20) if before[i * STRIDE:i * STRIDE + 16] != ram[SLOT0 + i * STRIDE:SLOT0 + i * STRIDE + 16]]
        img_c = screen(ctrl)
        pal = [snap_render.st_colour(w) for w in load_video_regs(ctrl)['palette_words']]
        boxes = overlay.boxes(L, layers, ram)
        ctl = {k: {(b.layer, b.index): b for b in overlay.boxes(L, control_layers(layers, k), ram)}
               for k in ('camera', 'origin+4')}
        rep(f'== {tag}: {SNAPS[tag]} -> run to ${SPRITE_PASS:x}, fork, run to ${AFTER_FLIP:x} (step {d.step_count}); '
            f'scroll $227b6 = {int.from_bytes(ram[0x227b6:0x227b8], "big")}; slots whose first 16 bytes changed '
            f'during the sprite pass: {moved or "none"}')
        rep(f'{"slot":<17} {"predicted x,y,w,h":<19} {"measured x0,y0-x1,y1":<22} {"offset":<9} {"px":>4} '
            f'{"frame":>5} {"fit@0":>6} {"best":>9}  | camera=$227b6: offset, at 0, best | origin+4: offset, at 0, best')
        res = []
        for b in boxes:
            slot_addr = b.addr
            d.restore(fork)
            d.poke(slot_addr, 2, 0)
            r = d.run(400_000, until_pc=AFTER_FLIP)
            assert r['reason'] == 'until', r
            gi = (b.addr - SLOT0) // STRIDE
            abl = d.save(os.path.join(OUT, f'{tag}_slot{gi}.snap'))
            changed = np.any(screen(abl) != img_c, axis=2)
            mb = bbox(changed)
            pb = (b.x, b.y, b.x + b.w - 1, b.y + b.h - 1)
            fr, pix = frame_pixels(ram, pal, slot_addr, b.x, b.y, b.h)
            row = f'{b.name:<17} {f"{b.x},{b.y},{b.w},{b.h}":<19} '
            if mb is None:
                rep(row + f'{"(no pixel changed)":<22} {"-":<9} {0:>4} {fr:>5}')
                res.append((tag, b.name, None))
                continue
            off = outside(pb, mb)
            s0, best, _sb = fit(changed, img_c, pix)
            ctl_txt = []
            for k in ('camera', 'origin+4'):
                cb = ctl[k][(b.layer, b.index)]
                cpb = (cb.x, cb.y, cb.x + cb.w - 1, cb.y + cb.h - 1)
                _f, cpix = frame_pixels(ram, pal, slot_addr, cb.x, cb.y, cb.h)
                cs0, cbest, _ = fit(changed, img_c, cpix)
                cbest = cbest if abs(cb.x - b.x) <= SHIFT else f'none within {SHIFT}'
                ctl_txt.append(f'{outside(cpb, mb)}, {cs0:.2f}, {cbest}')
            rep(row + f'{f"{mb[0]},{mb[1]}-{mb[2]},{mb[3]}":<22} {str(off):<9} {int(changed.sum()):>4} {fr:>5} '
                f'{s0:>6.2f} {str(best):>9}  | ' + ' | '.join(ctl_txt))
            res.append((tag, b.name, off, best, s0))
        return res
    finally:
        d.close()


def main():
    tags = sys.argv[1:] or list(SNAPS)
    os.makedirs(OUT, exist_ok=True)
    L = layout.load(LAYOUT)
    layers = overlay.load_overlay(L, LAYOUT)
    lines = []

    def rep(s):
        print(s)
        lines.append(s)
    allres = []
    for t in tags:
        allres += run_tag(t, L, layers, rep)
    meas = [r for r in allres if r[2] is not None]
    inside = sum(r[2] == (0, 0) for r in meas)
    zero = sum(r[3] == (0, 0) for r in meas)
    full = sum(r[4] == 1.0 for r in meas)
    rep(f'== summary: {len(allres)} live slots, {len(meas)} with changed pixels; measured box inside the predicted box '
        f'{inside}/{len(meas)}; best frame shift (0,0) {zero}/{len(meas)}; frame at the predicted position explains every '
        f'changed pixel {full}/{len(meas)}')
    with open(os.path.join(OUT, 'report.txt'), 'w') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
