"""Terrain attribute map of a level: the table `$ebb0` reads (the pool B solid records 24..31 it also checks are not in it).
   attribute(level, x, y) = word at  $60000[level] -> [((x >> 8) + ((y & $ff00) >> 4)) * 4] -> tilepage + 2 * (((x & $f0) >> 4) + (y & $f0))
   (transcribed from the listing at $ebb0..$ec22; the level 5 scroll-relative variant for `$80400` bit 6 is not done).
usage: terrain.py <level> <x0> <x1> <y0> <y1>   prints one character per 16 x 16 tile: '.' attribute 0, else the high byte in hex digits of the word
       terrain.py <level> <x0> <x1> <y0> <y1> -v   prints the words"""
import os, struct, sys
ROOT = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
ROM = open(os.path.join(ROOT, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def L(a): return struct.unpack(">I", ROM[a:a+4])[0]
def W(a): return struct.unpack(">H", ROM[a:a+2])[0]
def attribute(level, x, y):
    pages = L(0x60000 + 4 * level)
    tile = L(pages + (((x >> 8) + ((y & 0xff00) >> 4)) * 4))
    return W(tile + 2 * (((x & 0xf0) >> 4) + (y & 0xf0)))
if __name__ == "__main__":
    lv, x0, x1, y0, y1 = (int(v, 0) for v in sys.argv[1:6]); verbose = "-v" in sys.argv
    print("level %d, x %d..%d (step 16), y %d..%d (step 16); columns are x, rows are y" % (lv, x0, x1, y0, y1))
    print("      " + " ".join("%4x" % x for x in range(x0 & ~15, x1 + 1, 16)))
    for y in range(y0 & ~15, y1 + 1, 16):
        print("%5d " % y + " ".join(("%04x" % attribute(lv, x, y)) if verbose or attribute(lv, x, y) else "   ." for x in range(x0 & ~15, x1 + 1, 16)))
