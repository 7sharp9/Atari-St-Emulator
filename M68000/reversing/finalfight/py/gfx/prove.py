"""prove.py: the decode proofs against MAME screenshots (384 x 224 RGB, pixel by pixel).  Reads the dump sets that
make_proof_dumps.sh writes into scratchpad/finalfight/gfx/dump (gfx RAM, work RAM, CPS-A/B registers, live palette,
screenshot of the same frame).  Prints one line per comparison and a summary.
Rules established by the comparison (and used by cpsgfx.compose):
  * the object list drawn in frame k is the one in object RAM at the end of frame k-1, read at the OBJ base register of
    frame k-1 (the CPS1 buffers the table one frame, cps1_v.cpp:3063-3069);
  * entries are drawn last to first (entry 0 on top);
  * everything else (tile maps, scroll, palette, layer order, priority masks) is the frame's own state."""
import os, sys
import numpy as np
from PIL import Image
from cpsgfx import *

D = os.path.join(SCR, "gfx", "dump")
SN = os.path.join(SCR, "run", "snap")
G = Gfx()


def ld(tag, k):
    g = np.fromfile(os.path.join(D, "%s_%d_gfxram.bin" % (tag, k)), dtype=">u2")
    r = Regs.from_bytes(open(os.path.join(D, "%s_%d_regs.bin" % (tag, k)), "rb").read())
    pens = np.fromfile(os.path.join(D, "%s_%d_pens.bin" % (tag, k)), dtype=np.uint8).reshape(-1, 3) \
        if os.path.exists(os.path.join(D, "%s_%d_pens.bin" % (tag, k))) else None
    shot = np.array(Image.open(os.path.join(SN, "%s_%d.png" % (tag, k))).convert("RGB"))
    return g, r, pens, shot


def frame_match(tag, k, fwd_obj=False):
    g, r, pens, shot = ld(tag, k)
    gm = g
    ob = None
    if k > 1 and not fwd_obj:
        gp, rp, _, _ = ld(tag, k - 1)
        ob = cps_base(rp.a[A_OBJ], 0x800)
        gm = g.copy()
        gm[ob // 2:ob // 2 + 0x400] = gp[ob // 2:ob // 2 + 0x400]
    img, _ = compose(G, gm, r, obj_base=ob)
    return int((img == shot).all(axis=2).sum()), shot


def main():
    tot_eq = tot = 0
    print("== palette: build_palette(gfx RAM) against MAME's live pens (palette device), 3072 pens")
    for tag, k in (("en", 1), ("en", 2), ("bo", 1), ("bo", 2), ("gp", 1), ("s1", 1), ("st2", 1)):
        p = os.path.join(D, "%s_%d_pens.bin" % (tag, k))
        if not os.path.exists(p):
            continue
        g, r, pens, _ = ld(tag, k)
        mine = build_palette(g[cps_base(r.a[A_PAL], 0x400) // 2:][:0xc00], r.b[B_PALCTRL // 2])
        print("  %s_%d: %d of 3072 pens equal" % (tag, k, int((mine == pens).all(axis=1).sum())))
    print("== one layer at a time (the layer-control words poked in work RAM; each frame k>=2; 86016 pixels each)")
    for name, tagL in (("sprites only", "gpL0"), ("scroll 1 only", "gpL1"), ("scroll 2 only", "gpL2"), ("scroll 3 only", "gpL3")):
        res = []
        for k in range(2, 7):
            m, shot = frame_match(tagL, k)
            res.append(m)
            tot_eq += m
            tot += shot.shape[0] * shot.shape[1]
        g, r, _, shot = ld(tagL, 6)
        print("  %-14s layer control %04x: frames 2-6 equal pixels %s   (non-background pixels in the shot: %d)" % (
            name, r.b[B_LAYER // 2], res, int((shot != shot[0, 0]).any(axis=2).sum())))
    print("== full composite (sprites, three tile layers, priority masks)")
    for tag, K in (("gp", 4), ("en", 2), ("bo", 2), ("s1", 2), ("st2", 1)):
        res = []
        for k in range(1 if K == 1 else 2, K + 1):
            m, shot = frame_match(tag, k)
            res.append(m)
            tot_eq += m
            tot += shot.shape[0] * shot.shape[1]
        print("  %-4s frames %s equal pixels %s of %d" % (tag, list(range(1 if K == 1 else 2, K + 1)), res, 224 * 384))
    print("== ablation (what the two sprite rules buy), frame 2 of en and bo, equal pixels")
    for tag in ("en", "bo"):
        g, r, _, shot = ld(tag, 2)
        gp, rp, _, _ = ld(tag, 1)
        ob = cps_base(rp.a[A_OBJ], 0x800)
        gm = g.copy(); gm[ob // 2:ob // 2 + 0x400] = gp[ob // 2:ob // 2 + 0x400]
        full = (compose(G, gm, r, obj_base=ob)[0] == shot).all(axis=2).sum()
        fwd = (compose(G, gm, r, obj_base=ob, rev=False)[0] == shot).all(axis=2).sum()
        cur = (compose(G, g, r)[0] == shot).all(axis=2).sum()
        print("  %s: both rules %d, entries first-to-last %d, this frame's object RAM at this frame's base %d" % (tag, full, fwd, cur))
    print("TOTAL (layer and composite comparisons above) %d of %d pixels equal" % (tot_eq, tot))


if __name__ == "__main__":
    main()
