"""Attack boxes of pool A types: table $6b000[type] -> [state] -> 4 words (x0 x1 y0 y1 relative to the record's x/y; mirrored for dir 1 by the code).
A state whose box is not all zero is a state in which the type can hurt a player (routine $f4f4/$f690/$f700 tests the box against the players' body box).
usage: boxes.py [type ...]"""
import os, struct, sys
ROOT = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
ROM = open(os.path.join(ROOT, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def L(a): return struct.unpack(">I", ROM[a:a+4])[0]
def S(a): return struct.unpack(">h", ROM[a:a+2])[0]
def box(t, s):
    p = L(0x6b000 + 4*t)
    q = L(p + 4*s)
    return tuple(S(q + 2*i) for i in range(4)), q
if __name__ == "__main__":
    ts = [int(x) for x in sys.argv[1:]] or range(80)
    for t in ts:
        row = []
        for s in range(24):
            try:
                bx, q = box(t, s)
            except Exception as e:
                break
            if any(bx): row.append("%x:%s" % (s, bx))
        print("type %d" % t, " ".join(row))
