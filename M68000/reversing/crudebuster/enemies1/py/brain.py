"""Decode the decision tables of routine $2438a (shared 'brain' of the heavier pool A types).
Case A (player's lane within [my y - 0x60 .. my y + 0x20 roughly]; see doc): type -> [distance bucket (dx>>4, 16)] -> [player action +46 & 15 (16)] -> [player byte +47 (n)] -> routine.
Case B / C: type -> [bucket] -> routine.   tables: A $24508, B $24644, C $24780.
usage: brain.py <type> [case A|B|C]   prints per bucket the set of routines reached (and whether they depend on the player's state)"""
import os, struct, sys, collections
ROOT = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
R = open(os.path.join(ROOT, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def L(a): return struct.unpack(">I", R[a:a+4])[0]
def case_ab(base, t):
    t1 = L(base + 4*t)
    out = {}
    for b in range(16):
        t2 = L(t1 + 4*b)
        out[b] = t2
    return out
def routines_A(t):
    t1 = L(0x24508 + 4*t); res = {}
    for b in range(16):
        t2 = L(t1 + 4*b)
        rs = collections.OrderedDict()
        for a in range(16):
            t3 = L(t2 + 4*a)
            # t3 is a table indexed by player byte +47 (unknown length): read entries until they stop looking like code addresses
            for k in range(8):
                v = L(t3 + 4*k)
                if 0x10000 <= v < 0x2c000 and v % 2 == 0: rs.setdefault(v, []).append((a, k))
                else: break
        res[b] = rs
    return res
def routines_BC(base, t):
    t1 = L(base + 4*t); return {b: L(t1 + 4*b) for b in range(16)}
if __name__ == "__main__":
    t = int(sys.argv[1])
    for case, base in (("A", 0x24508), ("B", 0x24644), ("C", 0x24780)):
        if len(sys.argv) > 2 and sys.argv[2] != case: continue
        print("type %d case %s" % (t, case))
        if case == "A":
            res = routines_A(t)
            for b, rs in res.items(): print("  bucket %x (dx %02x-%02x): %s" % (b, b*16, b*16+15, " ".join("%x(%d)" % (r, len(v)) for r, v in rs.items())))
        else:
            res = routines_BC(base, t)
            for b, v in res.items(): print("  bucket %x (dx %02x-%02x): %x" % (b, b*16, b*16+15, v))
