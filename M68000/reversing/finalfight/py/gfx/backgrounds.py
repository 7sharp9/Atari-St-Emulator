"""backgrounds.py: scroll-2 and scroll-3 backgrounds per stage, assembled from every dump of that stage.

A dump holds a 64 x 64 tile map per layer (scroll 2: 16x16 tiles, 1024 x 1024 px; scroll 3: 32x32 tiles, 2048 x 2048 px).
The game does not keep the stage there, it streams columns: the area start routines (`$62bce`, `$62c06`, `$62c66`
...) fill 42 columns of 16 px (scroll 2) starting 9 columns left of the camera and 22 columns of 32 px (scroll 3)
starting 5 columns left of camera 2, and the run state streams one more column when bit 4 of the camera x changes
(transitions.md, "The camera").  A map column holds world column (x >> 4) mod 64.  So a dump is trusted for the world
columns [camcol - 9, camcol + 33) (scroll 2) and [camcol3 - 5, camcol3 + 17) (scroll 3); the rest of its map is
stale or not yet streamed.  Where two dumps claim the same world column their entries are compared and the number of
disagreements is printed (tile patches, doors and blinking lights account for some).
World x of the left screen edge = 46(A5) for scroll 2 and 54(A5) for scroll 3 (the CPS register holds that minus $40:
VBL routine `$5e8`); the vertical band shown is the visible rows plus two rows of margin.
Usage: python backgrounds.py   -> scratchpad/finalfight/gfx/out/bg/ and a coverage table on stdout."""
import collections, glob, hashlib, os, sys
import numpy as np
from PIL import Image, ImageDraw
from cpsgfx import *
import sheetlib as S
from census import dumps

OUTD = os.path.join(OUT, "bg")
os.makedirs(OUTD, exist_ok=True)


def info(gp, rp):
    ram = np.fromfile(rp, dtype=">u2")
    raw = open(rp, "rb").read()
    w = lambda d: int(ram[(0x8000 + d) // 2])
    regs = regs_from_ram(ram)
    return dict(stage=raw[0x8000 + 190], area=raw[0x8000 + 191], cam2x=w(46), cam2y=w(48), cam3x=w(54), cam3y=w(56),
                regs=regs, name=os.path.relpath(gp, SCR).replace("/", "_")[:-len("_gfxram.bin")])


def is_map_screen(G, g, r):
    """The stage-select map (and other full-screen scenes) leave the lower half of the picture empty: every pixel of the
    bottom 112 rows equals the background pen.  Their maps and camera values are leftovers of the previous stage, so
    they are not used as background evidence."""
    img, pen = compose(G, g, r)
    return bool((pen[112:] == pen[-1, -1]).all())


def main():
    G = Gfx()
    ds = dumps()
    D = []
    skipped = []
    for gp, rp in ds:
        d = info(gp, rp)
        g = np.fromfile(gp, dtype=">u2")
        r = d["regs"]
        if is_map_screen(G, g, r):
            skipped.append(os.path.relpath(gp, SCR))
            continue
        d["pal"] = build_palette(g[cps_base(r.a[A_PAL], 0x400) // 2:][:0xc00], 0x3f)
        d["l2"] = tile_grid(2, g, cps_base(r.a[A_S2B], 0x4000))
        d["l3"] = tile_grid(3, g, cps_base(r.a[A_S3B], 0x4000))
        d["s2y"] = s16(r.a[A_S2Y])
        d["s3y"] = s16(r.a[A_S3Y])
        D.append(d)
    print("not gameplay (empty lower half): %d dumps skipped" % len(skipped))
    by_stage = collections.defaultdict(list)
    for d in D:
        by_stage[d["stage"]].append(d)
    report = []
    for st in sorted(by_stage):
        for L, ts, win, cx, sy_key, camkey in ((2, 16, (-9, 33), "cam2x", "s2y", "l2"), (3, 32, (-5, 17), "cam3x", "s3y", "l3")):
            cols = {}                       # world col -> list of (dump index, band rows tuple)
            bands = collections.Counter()
            for di, d in enumerate(by_stage[st]):
                nrows = 224 // ts
                top = ((d[sy_key] + 16) // ts) % 64
                band = [(top - 2 + k) % 64 for k in range(nrows + 4)]
                bands[(top)] += 1
            # one strip per vertical band (rows are modulo 64: different camera y = different band)
            for top, _ in bands.items():
                members = [(di, d) for di, d in enumerate(by_stage[st]) if ((d[sy_key] + 16) // ts) % 64 == top]
                nrows = 224 // ts
                band = [(top - 2 + k) % 64 for k in range(nrows + 4)]
                claim = collections.defaultdict(list)
                for di, d in members:
                    cc = d[cx] // ts
                    for wc in range(cc + win[0], cc + win[1]):
                        if wc < 0:
                            continue
                        mc = wc & 63
                        code, attr = d[camkey]
                        col = (code[band, mc].copy(), attr[band, mc].copy())
                        claim[wc].append((di, d, col, abs(wc - (cc + 12 if L == 2 else cc + 6))))
                if not claim:
                    continue
                lo, hi = min(claim), max(claim)
                conflicts = overlaps = 0
                for wc, lst in claim.items():
                    if len(lst) > 1:
                        overlaps += 1
                        ref = lst[0][2]
                        if any((o[2][0] != ref[0]).any() or ((o[2][1] & 0x1ff) != (ref[1] & 0x1ff)).any() for o in lst[1:]):
                            conflicts += 1
                width = hi - lo + 1
                W = width * ts
                strip = np.zeros((len(band) * ts, W, 4), dtype=np.uint8)
                have = np.zeros(width, bool)
                for wc in range(lo, hi + 1):
                    if wc not in claim:
                        continue
                    di, d, col, _ = min(claim[wc], key=lambda t: t[3])
                    img = render_tiles(G, L, col[0][:, None], col[1][:, None], d["pal"])
                    strip[:, (wc - lo) * ts:(wc - lo + 1) * ts] = img
                    have[wc - lo] = True
                # runs of covered columns
                runs = []
                i = 0
                while i < width:
                    if have[i]:
                        j = i
                        while j < width and have[j]:
                            j += 1
                        runs.append((lo + i, lo + j - 1))
                        i = j
                    else:
                        i += 1
                im = Image.new("RGB", (W, strip.shape[0] + 14), S.BG)
                Image.fromarray(strip, "RGBA")
                big = Image.fromarray(strip, "RGBA")
                bgc = Image.new("RGB", big.size, (20, 20, 28))
                bgc.paste(big, (0, 0), big)
                im.paste(bgc, (0, 14))
                dr = ImageDraw.Draw(im)
                dr.text((2, 1), "stage %d scroll %d band rows %d..%d  world x %d-%d (columns %d-%d), %d dumps" % (
                    st, L, band[0], band[-1], lo * ts, (hi + 1) * ts, lo, hi, len(members)), font=S.FONT_S, fill=S.FG)
                for c in range(lo, hi + 1):
                    if (c * ts) % 256 == 0:
                        dr.line([((c - lo) * ts, 12), ((c - lo) * ts, 18)], fill=(255, 200, 60))
                        dr.text(((c - lo) * ts + 2, 1), "$%x" % (c * ts), font=S.FONT_S, fill=(255, 200, 60))
                fn = "stage%d_scroll%d_band%d.png" % (st, L, top)
                im.save(os.path.join(OUTD, fn), optimize=True)
                report.append((st, L, top, len(members), [(a * ts, (b + 1) * ts) for a, b in runs], overlaps, conflicts, fn,
                               os.path.getsize(os.path.join(OUTD, fn))))
    for r in report:
        print("stage %d scroll %d band top %2d: %3d dumps, world x runs %s, overlapping columns %d, disagreeing %d  %s (%d B)" % (
            r[0], r[1], r[2], r[3], ", ".join("$%x-$%x" % x for x in r[4]), r[5], r[6], r[7], r[8]))


if __name__ == "__main__":
    main()
