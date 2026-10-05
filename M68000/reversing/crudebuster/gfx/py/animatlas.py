"""Compose actor animation frames from the $30000 database (part format proven by emitcheck.py) into PNGs:
assets/anim_types_state0.png  (frame 0 of state 0 of every type, level-0 sprite palette)  and assets/anim_type<N>.png (every state/frame of one type)."""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cbrender as R, palsets as P, levelmaps as M
W, L, ROM = P.W, P.L, P.ROM
ROOT = P.ROOT

def sgn(v): return v - 0x10000 if v & 0x8000 else v

def compose(fptr, pal, canvas, ox, oy):
    g = R.gfx().sprites
    n = W(fptr)
    for i in range(n):
        p = fptr + 2 + 8 * i
        xoff, yoff, code = sgn(W(p)), sgn(W(p + 2)), W(p + 4)
        b6, b7 = ROM[p + 6], ROM[p + 7]
        yw = b6 << 8
        t = ((yw >> 10) & 1) << 1 | ((yw >> 9) & 1); multi = (1 << t) - 1
        fx, fy = (yw >> 13) & 1, (yw >> 14) & 1
        col = (b7 << 9 >> 9) & 0x1f
        base = (0x500 if col >= 16 else 0x100) + (col & 15) * 16
        code &= ~multi
        for m in range(multi + 1):
            tile = g[((code + multi - m) if not fy else (code + m)) % len(g)]
            if fx: tile = tile[:, ::-1]
            if fy: tile = tile[::-1, :]
            x0 = ox - xoff; y0 = oy - yoff - 16 * m      # the sprite words hold (cam - obj + off): decospr's x = 240 - x, y = 240 - y negate the offsets; tiles stack upwards (ypos = y - 16 * multi)
            for ty in range(16):
                for tx in range(16):
                    v = tile[ty, tx]
                    xx, yy = x0 + tx, y0 + ty
                    if v and 0 <= xx < canvas.shape[1] and 0 <= yy < canvas.shape[0]:
                        canvas[yy, xx] = pal[base + int(v)]

def main():
    pal = M.level_palette(0)
    ntypes = (L(0x30000) - 0x30000) // 4
    cell = 128
    cols = 10
    sheet = np.full((((ntypes + cols - 1) // cols) * cell, cols * cell, 3), 60, np.uint8)
    for t in range(ntypes):
        sp = L(0x30000 + 4 * t)
        ap = L(sp)
        if not (0x30000 <= ap < 0x7fff0): continue
        fptr = L(ap + 4)
        c = np.full((cell, cell, 3), 60, np.uint8)
        compose(fptr, pal, c, cell // 2, cell - 24)
        r, cc = divmod(t, cols)
        sheet[r * cell:(r + 1) * cell, cc * cell:(cc + 1) * cell] = c
    Image.fromarray(sheet).save(os.path.join(ROOT, "assets", "anim_types_state0.png"))
    # type 0 all states
    sp = L(0x30000); nst = 1; lo = L(sp)
    while sp + 4 * nst < lo: lo = min(lo, L(sp + 4 * nst)); nst += 1
    rows = []
    for s in range(nst):
        ap = L(sp + 4 * s)
        if not (0x30000 <= ap < 0x7fff0): continue
        last = ROM[ap + 1]
        row = np.full((cell, cell * min(last + 1, 12), 3), 60, np.uint8)
        for k in range(min(last + 1, 12)):
            c = np.full((cell, cell, 3), 60, np.uint8)
            compose(L(ap + 4 + 4 * k), pal, c, cell // 2, cell - 24)
            row[:, k * cell:(k + 1) * cell] = c
        full = np.full((cell, cell * 12, 3), 60, np.uint8); full[:, :row.shape[1]] = row
        rows.append(full)
    Image.fromarray(np.concatenate(rows, axis=0)).save(os.path.join(ROOT, "assets", "anim_type0.png"))
    print("types", ntypes, "type0 states", nst)

if __name__ == "__main__":
    main()
