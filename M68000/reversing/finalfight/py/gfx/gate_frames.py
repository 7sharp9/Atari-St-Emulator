"""gate_frames.py [tag ...]: the Python port of the object-list builder (`ffframes.build`) against the live object
RAM.  For every in-use record of the direct-draw pools in a dump (work RAM + gfx RAM), build the entries the game's
`$16910` would write (record x/y/mirror/palette override/x offset, camera `1042/1046(A5)`, frame block `36(A0)`)
and look for them as one contiguous run in either object buffer ($900000 or $904000, 0x400 words each).
Pools: tag at +18, 0 (players), 2 (fighters), 4 (bosses) (skipped when 64(A0) != 0: grapple draws), 8, $c, $12, $14 (draw
dispatch `$1685e`).  Prints per dump: records tested, matched, and the layout kinds of the matched and missed ones.
Dumps default to scratchpad/finalfight/gfx/dump/<tag>_<k>_{ram,gfxram}.bin (gfxdump.lua); a tag of the form
dir:name reads <dir>/<name>_ram.bin and _gfxram.bin."""
import os, sys, collections
import numpy as np
import ffframes as F
from cpsgfx import SCR

POOLS = [(0xff8568, 59, 0xc0), (0xffb228, 1, 0xc0), (0xffb2e8, 16, 0xc0), (0xffbee8, 10, 0xc0),
         (0xffc668, 30, 0x40), (0xff3000, 271, 0x40)]
DIRECT = {0, 2, 4, 8, 0xc, 0x12, 0x14}


def load(spec):
    if ":" in spec:
        d, name = spec.split(":", 1)
    else:
        d, name = os.path.join(SCR, "gfx", "dump"), spec
    ram = open(os.path.join(d, name + "_ram.bin"), "rb").read()
    gfx = np.fromfile(os.path.join(d, name + "_gfxram.bin"), dtype=">u2")
    return ram, gfx


def run(spec, verbose=False):
    ram, gfx = load(spec)
    A5 = 0x8000

    def b(off):
        return ram[off]

    def wd(off):
        return int.from_bytes(ram[off:off + 2], "big")

    def lg(off):
        return int.from_bytes(ram[off:off + 4], "big")

    camx = wd(A5 + 1042)
    camy = wd(A5 + 1046)
    bufs = []
    for base in (0x0, 0x4000):
        ob = gfx[base // 2:base // 2 + 0x400].astype(int).reshape(-1, 4)
        n = len(ob)
        for i in range(len(ob)):
            if (ob[i, 3] & 0xff00) == 0xff00:
                n = i
                break
        bufs.append([tuple(int(v) for v in e) for e in ob[:n]])
    tested = matched = 0
    kinds_ok = collections.Counter()
    kinds_bad = collections.Counter()
    bad = []
    for base, count, stride in POOLS:
        for i in range(count):
            r = base + i * stride - 0xff0000
            if b(r) == 0:
                continue
            tag = b(r + 18)
            if tag not in DIRECT:
                continue
            if tag in (0, 2, 4) and b(r + 64):          # held/holding record: drawn by its partner, `$16876`
                continue
            if b(r + 1) == 0:                      # visibility byte: `tst.b 1(A0) ; beq` at $16910
                continue
            blk = lg(r + 36)
            if not F.frame_ok(blk):
                continue
            ent = F.build(blk, wd(r + 6), wd(r + 10), camx, camy, mirror=bool(b(r + 46)), pal=b(r + 47), xoff=wd(r + 48))
            if not ent:
                continue
            tested += 1
            hit = False
            for buf in bufs:
                for s in range(len(buf) - len(ent) + 1):
                    if all(buf[s + j] == ent[j] for j in range(len(ent))):
                        hit = True
                        break
                if hit:
                    break
            kind = F.rom[blk] // 4
            if hit:
                matched += 1
                kinds_ok[kind] += 1
            else:
                kinds_bad[kind] += 1
                bad.append((hex(base + i * stride), tag, hex(blk), kind))
    print("%-30s records tested %3d matched %3d   kinds matched %s  missed %s" % (
        spec, tested, matched, dict(sorted(kinds_ok.items())), dict(sorted(kinds_bad.items()))))
    if verbose:
        for x in bad:
            print("   miss", x)
    return tested, matched


if __name__ == "__main__":
    verbose = "-v" in sys.argv[1:]
    args = [a for a in sys.argv[1:] if a != "-v"] or ["gp_1", "gp_2", "en_1", "en_2", "bo_1", "bo_2", "st2_1"]
    tt = mm = 0
    for a in args:
        if a == "-v":
            continue
        t, m = run(a, verbose)
        tt += t
        mm += m
    print("total tested %d matched %d" % (tt, mm))
