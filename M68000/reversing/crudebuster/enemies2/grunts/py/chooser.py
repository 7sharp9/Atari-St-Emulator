"""chooser.py <type hex> [tstate hex] [tsub dec]: the attack chooser $2438a of a pool A type, expanded to the states it can start.
 For each dx bucket (dx>>4, dx = horizontal distance to the target, 0..$ff; dx >= $100 -> state 7) and each of the three tables
 (T1 same lane, table $24508, keyed also by the target's state +46&$f and sub-state +47 (default 0 and 0); T2 enemy more than $60 below the target: $24644;
 T3 enemy at least $20 above the target: $24780) it prints the probability of each resulting state.
 A leaf routine either sets a state directly (first `move.b #S,3(A6)` in its body) or is a random pick: `btst #7,1(A6)` (only on an animation wrap),
 `jsr $ea44`, `andi.w #M,D0`, a table of M+1 longword routine addresses; each entry is resolved the same way (state = first `move.b #S,3(A6)`;
 `*` marks a routine that first sets a jump parameter via $2280c/$22844 (a jump state), `?` an entry whose body sets no state).
 Rows group consecutive dx buckets with the same distribution."""
import os, sys, re, collections
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
lin = {}
for line in open(os.path.join(root, "scratchpad/crudebuster/all_lin.txt")):
    a, _, ins = line.strip().partition(": ")
    lin[int(a[1:], 16)] = ins
def l(a): return int.from_bytes(rom[a:a+4], "big")
def body(a, n=40):
    out = []
    p = a
    while len(out) < n and p < 0x2c000:
        ins = lin.get(p)
        if ins is None: p += 2; continue
        out.append((p, ins)); p += 2
        if ins.startswith("rts"): break
    return out
def state_of(a, depth=0):
    """(state, note) set by the first `move.b #S,3(A6)` in routine a (a leading jsr/bsr to code is followed once)"""
    note = ""
    for p, ins in body(a):
        mj = re.match(r"(?:jsr|bsr|bra) (?:-?\d+\(PC\) == |)\$([0-9a-f]+)", ins)
        if mj and depth == 0 and not ins.startswith("jsr $e") and "$ea44" not in ins and int(mj.group(1), 16) < 0x2c000 and int(mj.group(1), 16) not in (0x22c2c, 0x2280c, 0x22844):
            st, n2 = state_of(int(mj.group(1), 16), 1)
            if st is not None: return st, note + n2
        if "$2280c" in ins or "$22844" in ins or "== $2280c" in ins or "== $22844" in ins: note = "*"
        m = re.match(r"move\.b #\$([0-9a-f]+),3\(A6\)", ins)
        if m: return int(m.group(1), 16), note
        if "(A6)" in ins and "3(A6)" in ins and "move" in ins and "#" not in ins: break
    return None, note
def leaf(a):
    """returns Counter state-> probability"""
    b = body(a, 30)
    txt = [i for _, i in b]
    c = collections.Counter()
    rnd = None
    for k, (p, ins) in enumerate(b):
        m = re.match(r"andi\.w #\$([0-9a-f]+),D0", ins)
        if m and any("$ea44" in t for t in txt[:k]):
            mask = int(m.group(1), 16)
            for q, ins2 in b[k:]:
                m2 = re.match(r"lea (-?\d+)\(PC\) == \$([0-9a-f]+),A0", ins2)
                if m2: rnd = (int(m2.group(2), 16), mask); break
    if rnd:
        t, mask = rnd
        for i in range(mask + 1):
            st, note = state_of(l(t + 4 * i))
            c[("%x" % st if st is not None else "?") + note] += 1.0 / (mask + 1)
        return c
    st, note = state_of(a)
    c[("%x" % st if st is not None else "?") + note] += 1.0
    return c
def fmt(c): return " ".join(f"{k}:{v:.3g}" for k, v in sorted(c.items()))
def main():
    ty = int(sys.argv[1], 16)
    ts = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0
    tsub = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    for name, base in (("T1 same lane", 0x24508), ("T2 enemy below", 0x24644), ("T3 enemy above", 0x24780)):
        p1 = l(base + 4 * ty)
        rows = []
        for b in range(16):
            p2 = l(p1 + 4 * b)
            if name.startswith("T1"):
                p3 = l(p2 + 4 * (ts & 15)); r = l(p3 + 4 * tsub)
            else: r = p2
            rows.append((r, fmt(leaf(r))))
        print(f"type {ty:02x} {name} (target state {ts:x}, sub {tsub}):")
        s = 0
        while s < 16:
            e = s
            while e + 1 < 16 and rows[e + 1][1] == rows[s][1]: e += 1
            print(f"   dx {s*16:3d}..{e*16+15:3d} [leaf ${rows[s][0]:06x}]: {rows[s][1]}")
            s = e + 1
        print("   dx >= 256: 7")
main()
