"""bgmaps.py: the pristine scroll-2 and scroll-3 maps of every stage, produced by the game's own streaming routines.

The level maps are not in RAM as such: they are chunk tables in the program ROM (scroll 2 chunks of 16 x 16 tiles at
$90000 + 1 KiB * id, scroll 3 chunks of 8 x 8 tiles at $80000 + 256 B * id) selected through a per-stage block table
(`$62586`, `$625e0`, `$62e1e`).  Rather than port those routines, callscript.lua calls them on a fake camera record:
  loader `$6263a` with 190(A5) = stage  (sets mode/pointer of camera records 1036(A5) and 1164(A5))
  per column: `$62d6c`, `$62db6`, `$62f88` (scroll 2, D5 = world x, D6 = ~(camera y + $180), A6 = $ff840c) and
              `$62d92`, `$62dec`, `$630c8` (scroll 3, A6 = $ff848c)
exactly the call order of the area start routines (`$62bec`, `$62c84`).  The map RAM is zeroed before each batch of 56
columns and read back after it, so the result is what the game itself writes, without tile patches, animation or
anything a run added.  Output: npy arrays (world columns x 64 rows x (code, attr)) per stage, layer and camera y, in
scratchpad/finalfight/gfx/out/pristine/ plus coverage on stdout.  About 1 minute of MAME time for stages 0-7.
Usage: python bgmaps.py [stage ...]"""
import os, subprocess, sys
import numpy as np
from cpsgfx import *

OUTD = os.path.join(OUT, "pristine")
os.makedirs(OUTD, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
# camera y values per stage (scroll 2 camera y, scroll 3 camera y): area starts of tables.txt, `$626c0`
Y2 = {0: [0], 1: [0], 2: [0], 3: [0, 0x800], 4: [0], 5: [0, 0x800], 6: [0], 7: [0]}
Y3 = {0: [0, 0xe0], 1: [0, 0x100, 0x210], 2: [0], 3: [0], 4: [0], 5: [0, 0x200], 6: [0xe], 7: [0]}
XMAX2 = {0: 0xd00, 1: 0x1500, 2: 0x1000, 3: 0x1000, 4: 0x2400, 5: 0x3400, 6: 0x400, 7: 0x500}
XMAX3 = {0: 0x1000, 1: 0x2400, 2: 0x1400, 3: 0x1400, 4: 0x1400, 5: 0x2000, 6: 0x1400, 7: 0x800}
BATCH = 56


def build(stage):
    cmds = ["P ff80be 1 %x" % stage, "P ff80bf 1 0", "S A5 ff8000", "C 6263a"]
    plan = []                                   # (layer, y, first world column, count)
    for L, ys, xmax, step, rec, seq, base, size in (
            (2, Y2[stage], XMAX2[stage], 16, "ff840c", ("62d6c", "62db6", "62f88"), 0x90c000, 0x4000),
            (3, Y3[stage], XMAX3[stage], 32, "ff848c", ("62d92", "62dec", "630c8"), 0x910000, 0x4000)):
        for y in ys:
            ncol = xmax // step
            for w0 in range(0, ncol, BATCH):
                n = min(BATCH, ncol - w0)
                cmds.append("Z %x %x" % (base, size))
                cmds.append("S A6 %s" % rec)
                for k in range(n):
                    cmds.append("S D5 %x" % ((w0 + k) * step))
                    cmds.append("S D6 %x" % ((~(y + 0x180)) & 0xffff))
                    for a in seq:
                        cmds.append("C %s" % a)
                cmds.append("R %x %x" % (base, size))
                plan.append((L, y, w0, n))
    return cmds, plan


def run(stage):
    cmds, plan = build(stage)
    tin = os.path.join(OUTD, "cmds_%d.txt" % stage)
    tout = os.path.join(OUTD, "out_%d.txt" % stage)
    open(tin, "w").write("\n".join(cmds) + "\n")
    env = dict(os.environ, FF_MAMEARGS="-debug -debugger none", CS_IN=tin, CS_OUT=tout)
    ncalls = sum(1 for c in cmds if c.startswith("C "))
    subprocess.run(["sh", os.path.join(ROOT, "reversing", "finalfight", "ffrun.sh"), os.path.join(HERE, "callscript.lua"),
                    str(max(600, ncalls // 15))], env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    lines = [l for l in open(tout) if l.startswith("R ")]
    assert len(lines) == len(plan), (len(lines), len(plan))
    res = {}
    for (L, y, w0, n), line in zip(plan, lines):
        words = np.frombuffer(bytes.fromhex(line.split()[2]), dtype=">u2")
        base = 0xc000 if L == 2 else 0x10000
        g = np.zeros(0x18000 + 0x8000, dtype=np.uint16)
        g[base // 2:base // 2 + 0x2000] = words
        code, attr = tile_grid(L, g, base)
        arr = res.setdefault((L, y), [])
        for k in range(n):
            mc = (w0 + k) & 63
            arr.append(np.stack([code[:, mc], attr[:, mc]], axis=1))
    for (L, y), arr in res.items():
        np.save(os.path.join(OUTD, "stage%d_s%d_y%04x.npy" % (stage, L, y)), np.array(arr))
    return res


if __name__ == "__main__":
    for st in ([int(a) for a in sys.argv[1:]] or range(8)):
        res = run(st)
        for (L, y), arr in sorted(res.items()):
            a = np.array(arr)
            nz = (a[:, :, 0] != 0).sum(axis=0)
            print("stage %d scroll %d camera y %04x: %d columns, rows with entries: %s" % (
                st, L, y, len(arr), [int(r) for r in np.where(nz > 0)[0]]))
