# Python half of the synthetic blit cross-check: Sprites.blitEntity mirrored with
# pm_render_ref primitives on blit_fs.fsx's data ($XCHECK_OUT/blit_py.txt).
import os, sys
from pathlib import Path
_here = Path(__file__).resolve().parent
_root = next(p for p in _here.parents if (p / "tools" / "rdis.py").exists())
sys.path.insert(0, str(_root / "tools"))
OUT = Path(os.environ.get("XCHECK_OUT", "."))
import pm_render_ref as P
def lcg(seed, n):
    a = bytearray(n); x = seed & 0xffffffff
    for i in range(n):
        x = (x*1103515245 + 12345) & 0xffffffff; a[i] = (x >> 16) & 0xff
    return bytes(a)
def decode33(sheet, idx):
    """$11f82 on the $33000 sheet: the mask is ANDed in and the planes ORed in
    unmasked, so a transparent pixel with plane bits k reads -1 - k (the screen
    ORed with k), as Sprites.decodeFrameAt. pm_render_ref._decode_frame_byte
    drops k, which only real sheets (k = 0 under the mask) agree with."""
    o = idx * 55
    px = [[-1] * 8 for _ in range(11)]
    if o + 55 > len(sheet):
        return px
    for r in range(11):
        m, p0, p1, p2, p3 = sheet[o + r * 5: o + r * 5 + 5]
        for x in range(8):
            bit = 7 - x
            k = (((p0 >> bit) & 1) | (((p1 >> bit) & 1) << 1) |
                 (((p2 >> bit) & 1) << 2) | (((p3 >> bit) & 1) << 3))
            px[r][x] = k if not ((m >> bit) & 1) else -1 - k
    return px
def put(idxbuf, cov, i, v):
    if v >= 0: idxbuf[i] = v; cov[i] = 1
    elif v < -1: idxbuf[i] |= -1 - v; cov[i] = 1
sheet33 = lcg(1, 0x160*55); sheetProp = lcg(2, 28*480)
W, Hh = P.W, P.H
c00, c10, c01, c11 = (120, 80), (150, 78), (122, 111), (151, 109)
yaw, rot = 0xf0, 2
rr = bytearray(0x58000); rr[0x57FED] = rot
ent = dict(anim=0, sel_group=1, tile_off=6, ram=bytes(rr),
           sheet33=sheet33, sheet_prop=sheetProp)
cases = [
 (0,1,0x10,0,0x20,0,128,100,0,0,0), (0,2,0x00,0,0x77,0,40,200,0,0,0),
 (0,3,0x90,0,0x05,0,200,30,0,0,60), (0,4,0x00,0,0xf0,0x32,10,10,0,0,0),
 (4,0,0x11,0,0,0,0,0,88,120,0), (4,0,0x0e,0,0,0,0,0,12,200,0),
 (4,0,0x0d,0,0,0,0,0,250,5,0), (8,0,0,0x33,0,0,150,150,0,0,0),
 (8,0,0,0x08,0,0,22,240,0,0,0), (14,1,0,0,0,0,90,90,0,0,0),
 (14,3,0,0,0,0,5,250,0,0,0), (24,0,0x10,0,0,0,0,0,0,0,0),
 (24,0,0x12,0,0,0,0,0,0,0,0)]
out = []
for k, (b6,b5,b7,b14,b17,b31,fx,fy,_,_,grp) in enumerate(cases):
    s = (0x47970 + 0x50000 + 0x2a * k) & 0xFFFF   # pm_render_ref line ~439
    fx4, fy4 = (s << 3) & 0xFF, (s + (0x3F364 & 0xFFFF)) & 0xFF
    o = dict(b6=b6,b5=b5,b7=b7,b14=b14,b17=b17,b31=b31,fx=fx,fy=fy,
             fx4=fx4,fy4=fy4,group=grp,wcx=0,wcy=0)
    idxbuf = bytearray(W*Hh); cov = bytearray(W*Hh)
    fr = P._entity_frame(o, ent, yaw)
    if fr is not None:
        kind, fi, w, h = fr
        def blit(frame, sx, sy):
            for r, rowpx in enumerate(frame):
                yy = sy + r
                if not (0 <= yy < Hh): continue
                for cc, v in enumerate(rowpx):
                    xx = sx + cc
                    if 0 <= xx < W: put(idxbuf, cov, yy*W+xx, v)
        if kind == "33":
            if b6 in (6, 24):
                cx = (c00[0]+c10[0]+c01[0]+c11[0]) >> 2
                cy = (c00[1]+c10[1]+c01[1]+c11[1]) >> 2
                pxp, pyp = cx-8+4, cy-8+8
            else:
                pxp, pyp = P._packed_lerp(c00, c10, c01, c11, o["fx"], o["fy"])
            blit(decode33(ent["sheet33"], fi), pxp-4, pyp-8)
        else:
            pxp, pyp = P._packed_lerp(c00, c10, c01, c11, o["fx4"], o["fy4"])
            blit(P._decode_frame_word(ent["sheet_prop"], fi, w, h, 480), pxp-8, pyp-16)
    px = [f"{x},{y},{idxbuf[y*W+x]}" for y in range(Hh) for x in range(W) if cov[y*W+x]]
    out.append(f"CASE b6={b6} b5={b5} b7={b7} b14={b14} b17={b17} b31={b31} "
               f"fx={fx} fy={fy} fx4={fx4} fy4={fy4} grp={grp} | " + " ".join(px))
# more melee men, as blit_fs.fsx's second list
for (b5, b7, b17, b31, b44, w18) in [(1, 0x00, 0x00, 0x32, 2, 0), (2, 0x10, 0x90, 0x34, 4, 0),
                                     (3, 0x00, 0x40, 0x32, 6, 0x1400), (4, 0x00, 0x40, 0x34, 6, 0x0a00)]:
    o = dict(b6=0, b5=b5, b7=b7, b14=0, b17=b17, b31=b31, fx=100, fy=120, group=0,
             wcx=0, wcy=0, b44=b44, w18=w18)
    idxbuf = bytearray(W*Hh); cov = bytearray(W*Hh)
    fr = P._entity_frame(o, ent, yaw)
    if fr is not None:
        pxp, pyp = P._packed_lerp(c00, c10, c01, c11, 100, 120)
        for r, rowpx in enumerate(decode33(ent["sheet33"], fr[1])):
            yy = pyp - 8 + r
            if not (0 <= yy < Hh): continue
            for cc, v in enumerate(rowpx):
                xx = pxp - 4 + cc
                if 0 <= xx < W: put(idxbuf, cov, yy*W+xx, v)
    px = [f"{x},{y},{idxbuf[y*W+x]}" for y in range(Hh) for x in range(W) if cov[y*W+x]]
    out.append(f"MELEE b5={b5} b7={b7} b17={b17} b31={b31} b44={b44} w18={w18} | " + " ".join(px))
open(OUT / "blit_py.txt", "w").write("\n".join(out) + "\n")
print("wrote", len(cases), "cases")
