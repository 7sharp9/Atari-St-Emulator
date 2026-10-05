"""State tables of the pool A type handlers: find every `lea d(PC) == $T,A0 / movea.l 0(A0,D0.w),A0 / jsr (A0)` dispatch inside a handler's address range
and read the longword table at T (entries are accepted while they point into [handler start, next handler start)).
usage: states.py [type ...]   prints per type: handler range, dispatch tables with entries (state index -> address)."""
import os, re, struct, sys
ROOT = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
ROM = open(os.path.join(ROOT, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
LIN = open(os.path.join(ROOT, "scratchpad/crudebuster/all_lin.txt")).read().split("\n")
def L(a): return struct.unpack(">I", ROM[a:a+4])[0]
H = [L(0x10418 + 4*i) for i in range(80)]
starts = sorted(set(H))
def hrange(t):
    s = H[t]; nxt = [x for x in starts if x > s]
    return s, (nxt[0] if nxt else 0x22000)
def tables(t):
    s, e = hrange(t)
    res = []
    for i, l in enumerate(LIN):
        m = re.match(r"\s+\$([0-9a-f]+): lea (-?\d+)\(PC\) == \$([0-9a-f]+),A0", l)
        if not m: continue
        a = int(m.group(1), 16)
        if not (s <= a < e): continue
        if i + 1 < len(LIN) and "movea.l 0(A0,D0.w),A0" in LIN[i+1]:
            T = int(m.group(3), 16); ent = []
            lim = T + 0x400
            while T + 4*len(ent) < lim:
                v = L(T + 4*len(ent))
                if not (0x10000 <= v < 0x2c000) or v & 1: break
                ent.append(v)
                if s <= v < e and v > T: lim = min(lim, v)
            res.append((a, T, ent))
    return res
if __name__ == "__main__":
    ts = [int(x) for x in sys.argv[1:]] or range(80)
    for t in ts:
        s, e = hrange(t)
        print("type %d handler $%x-$%x" % (t, s, e))
        for a, T, ent in tables(t):
            print("  dispatch at $%x table $%x: %s" % (a, T, " ".join("%x:%x" % (i, v) for i, v in enumerate(ent))))
