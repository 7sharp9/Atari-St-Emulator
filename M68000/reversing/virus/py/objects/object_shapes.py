"""What each object-map type draws: A/B renders with the cell present and with its map byte zeroed.

    uv run python object_shapes.py <snap> <out_dir> [--types 1,2,...] [--n 3] [--flags 0x00,0x10,0x20]

For each type t and each of n chosen cells (map byte low 5 bits = t, flags 0, the 3 x 3 cells around it all zero,
ground height <= $510) the camera is put in front of the cell (the pokes below: ship x = col*256 + $100,
z = row*256 - $180, y = ground - $380, velocity 0, at 7 arrivals at $255c2; the pokes are the only intervention) and
the live screen is written twice from the same snapshot with the same pokes: A with the cell as it is (flags forced to
each value of --flags by a poke of the map byte before the run), B with the byte zeroed (the control: the same frame
without the object). The pixels that differ are the object; the script prints their count and bounding box and whether
the predicted base position of the cell (sx = 160 + (col*256 - camx)*256/depth, sy = 70 + (h - camy)*256/depth,
depth = row*256 - camz + $e00) lies inside the box horizontally and at or just above its lower edge. Writes PNGs
(A, B, and a 4x crop of the difference) under <out_dir>; reads nothing else.
"""
import struct
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon
from vcommon import ROOT, WORK, work
from stclient import StServer
from PIL import Image
import numpy as np

def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v

DX, DZ, CLEAR = 0x100, 0x180, 0x380

POSES = [(0x100, 0x180, 0x380), (-0x100, 0x280, 0x300), (0x0c0, 0x400, 0x480), (-0x0c0, 0x200, 0x340), (0x100, 0x300, 0x400)]

def shoot(snap, row, col, byte, path, pose=(DX, DZ, CLEAR)):
    s = StServer(ROOT)
    try:
        s('load', snapshot=snap)
        s('bp_set', addrs=[0x255c2])
        hb = s.read(0x42a58 + row * 256 + col, 1)[0]
        h = s16(hb * 8 + 0xfd68)
        s('poke', addr=0x32a58 + row * 256 + col, width=1, value=byte)      # labelled poke: the cell's map byte
        dx, dz, clear = pose
        x = col * 256 + dx; z = row * 256 - dz; y = h - clear
        for n in range(7):
            r = s('run', max_steps=3000000); assert r['reason'] == 'breakpoint', r
            for off, v in zip(range(0, 12, 2), (x, y, z, 0, 0, 0)):
                s('poke', addr=0x270b0 + off, width=2, value=v & 0xffff)
        r = s('run', max_steps=3000000); assert r['reason'] == 'breakpoint', r
        cam = struct.unpack('>3h', s.read(0x270ce, 6))
        s('render', path=path)
        return h, cam
    finally:
        s.close()

def main():
    a = sys.argv[1:]
    opt = lambda k, dflt: a[a.index(k) + 1] if k in a else dflt
    types = [int(v) for v in opt('--types', '1,2,3,4,5,6,7,8,9,10,11,12').split(',')]
    n = int(opt('--n', '3'))
    flags = [int(v, 0) for v in opt('--flags', '0x00').split(',')]
    pos = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or not a[i - 1].startswith('--'))]
    snap, out = os.path.abspath(pos[0]), pos[1]
    os.makedirs(out, exist_ok=True)
    r = vcommon.load_ram(snap)
    mp = r[0x32a58:0x32a58 + 65536]; hm = r[0x42a58:0x42a58 + 65536]
    def clean(i):
        row, col = i >> 8, i & 255
        if not (3 <= row < 120 and 3 <= col < 120): return False     # the ship's words are signed: stay below $8000
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                j = i + dr * 256 + dc
                if j != i and mp[j]: return False
        h = s16(hm[i] * 8 + 0xfd68)
        return h <= 0x510 and 0 <= row * 256 - 0 and (row >= 12 or col >= 12)   # off the pad
    tot = {}
    ext = {}
    explicit = {}
    for c in opt('--cells', '').split(';'):
        if c:
            t_, rc = c.split(':'); r_, c_ = rc.split(','); explicit.setdefault(int(t_), []).append(int(r_) * 256 + int(c_))
    for t in types:
        cells = explicit.get(t) or [i for i in range(65536) if (mp[i] & 0x1f) == t and (mp[i] >> 5) == 0 and clean(i)]
        step = max(1, len(cells) // n)
        for i in cells[::step][:n]:
            row, col = i >> 8, i & 255
            pose = POSES[(row + col) % len(POSES)]
            for fl in flags:
                tag = f't{t}_f{fl:02x}_r{row}_c{col}'
                pa, pb = os.path.join(out, tag + '_A.png'), os.path.join(out, tag + '_B.png')
                h, cam = shoot(snap, row, col, t | fl, pa, pose)
                shoot(snap, row, col, 0, pb, pose)
                A = np.array(Image.open(pa).convert('RGB')).astype(int); B = np.array(Image.open(pb).convert('RGB')).astype(int)
                depth = row * 256 - cam[2] + 0xe00
                sx = 160 + (col * 256 - cam[0]) * 256 / depth; sy = 70 + (h - cam[1]) * 256 / depth
                m = (A != B).any(axis=2); m[:14, :] = False       # ignore the HUD strip
                win = np.zeros_like(m)                             # the ship's trail sparks differ by RNG: keep a window round the cell
                win[max(0, int(sy) - 60):int(sy) + 22, max(0, int(sx) - 34):int(sx) + 35] = True
                m &= win
                ys, xs = np.nonzero(m)
                if len(xs):
                    box = (xs.min(), ys.min(), xs.max(), ys.max())
                    inside = box[0] - 2 <= sx <= box[2] + 2 and box[1] - 2 <= sy <= box[3] + 2
                    hin = box[0] - 2 <= sx <= box[2] + 2
                    ext.setdefault((t, fl), []).append((round((box[1] - sy) * depth / 256), round((box[3] + 1 - sy) * depth / 256), round((box[0] - sx) * depth / 256), round((box[2] + 1 - sx) * depth / 256)))
                    wrong = box[0] - 2 <= sx + 2 * 256 * 256 / depth <= box[2] + 2      # control: the cell two columns over (columns only)
                    Image.fromarray(np.where(m[..., None], A, 0).astype('uint8')).crop((max(0, box[0] - 6), max(0, box[1] - 6), min(320, box[2] + 7), min(200, box[3] + 7))).resize(((box[2] - box[0] + 13) * 4, (box[3] - box[1] + 13) * 4), Image.NEAREST).save(os.path.join(out, tag + '_D.png'))
                else:
                    box, inside, wrong = None, False, False
                tot.setdefault((t, fl), []).append((inside, wrong, hin if box else False))
                box = tuple(int(v) for v in box) if box else None
                print(f'type {t:2d} flags ${fl:02x} cell ({row:3d},{col:3d}) cam {cam} diff px {int(m.sum()):5d} box {box} base ({sx:.0f},{sy:.0f}) base-in-box {inside} (control, columns of cell +2: {wrong}) pose {pose}')
    for k, v in sorted(tot.items()):
        print(f'type {k[0]:2d} flags ${k[1]:02x}: base inside the object box {sum(x[0] for x in v)}/{len(v)}; sx inside the box columns {sum(x[2] for x in v)}/{len(v)}; control (sx of the cell two columns over inside the box columns) {sum(x[1] for x in v)}/{len(v)}')
    for k, v in sorted(ext.items()):
        print(f'type {k[0]:2d} flags ${k[1]:02x} extents (top, bottom, left, right; world units from the cell vertex): {v}')
main()
