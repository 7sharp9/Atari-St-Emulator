"""Decode the AI chooser ($2438a) tables of a pool A type into the states the enemy can enter.
For every distinct leaf routine of tables T1 ($24508, same level), T2 ($24644, enemy far below the target), T3 ($24780, enemy above the target)
the leaf is walked (linear listing, to its first rts): `move.b #S,3(A6)` = new state S (hex), `lea N(PC),A0 ... movea.l 0(A0,D0.w),A1 / jsr (A1)` = a
4-way choice made with `$ea44 & 3` over a table of longword routines (decoded recursively), a direct `jsr`/`bsr` to code is followed.
Output per type: for each table the dx>>4 buckets (each bucket 16 px of |dx| = distance to the target x) grouped by leaf, and the leaf's outcome.
usage: chooser.py <type hex> [T1|T2|T3] ; --leafs prints just the distinct leaves with outcome.
Read: all_lin.txt is the linear listing; the 4-way tables are read from the ROM image (longwords)."""
import os, sys, re
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
lin = {}
for line in open(os.path.join(root, "scratchpad/crudebuster/all_lin.txt")):
    a, _, ins = line.strip().partition(": ")
    lin[int(a[1:], 16)] = ins
def l(a): return int.from_bytes(rom[a:a+4], "big")
T = {"T1": 0x24508, "T2": 0x24644, "T3": 0x24780}

def walk(addr, depth=0, seen=None):
    """returns a list of outcome strings for the leaf routine at addr"""
    seen = seen or set()
    if addr in seen or depth > 4: return ["..."]
    seen = seen | {addr}
    out = []
    a = addr
    pend_tab = None
    while a in lin and a < addr + 0x200:
        ins = lin[a]
        m = re.match(r"move.b #\$([0-9a-f]+),3\(A6\)", ins)
        if m: out.append("state %x" % int(m.group(1), 16))
        m = re.match(r"lea (-?\d+)\(PC\) == \$([0-9a-f]+),A0", ins)
        if m and ("0(A0,D0.w),A1" in lin.get(a + 6, "") or "0(A0,D0.w),A1" in lin.get(a + 4, "") or "0(A0,D0.w),A1" in lin.get(a + 8, "")):
            t = int(m.group(2), 16)
            alts = [walk(l(t + 4 * i), depth + 1, seen) for i in range(4)]
            out.append("rand4[" + " | ".join(",".join(x) for x in alts) + "]")
        m = re.match(r"(?:jsr|bsr) (?:-?\d+\(PC\) == )?\$([0-9a-f]+)(?:\.l)?$", ins)
        if m:
            t = int(m.group(1), 16)
            if t in (0x22c2c, 0x22b48, 0x22bd0, 0xea44): pass
            elif t == 0x2280c: out.append("jumpparams(D7)")
            elif t >= 0x24000 and t < 0x28000 and t not in (0x24022, 0x24056):
                out += walk(t, depth + 1, seen)
        m2 = re.match(r"move.w #\$([0-9a-f]+),D7", ins)
        if ins.startswith("rts"): break
        a += 2 if a + 2 in lin else 2
        # linear listing addresses are not all +2 apart; step to the next known address
        nxt = [x for x in range(a, a + 8, 2) if x in lin]
        if not nxt: break
        a = nxt[0]
    return out

def dump(ty, name, leafs_only=False):
    base = T[name]
    p1 = l(base + 4 * ty)
    buckets = {}
    for b in range(16):
        p2 = l(p1 + 4 * b)
        if name == "T1":
            for s in range(16):
                p3 = l(p2 + 4 * s)
                subs = []
                for k in range(16):
                    t = l(p3 + 4 * k)
                    if not (0x400 <= t < 0x2c000): break
                    subs.append(t)
                buckets.setdefault((b,), set()).add((s, tuple(subs)))
        else:
            buckets[(b,)] = {(None, (p2,))}
    print(f"== type {ty:02x} {name} table ${p1:06x}")
    leaf = {}
    for (b,), vals in buckets.items():
        for s, subs in vals:
            for t in subs: leaf.setdefault(t, set()).add(b)
    for t, bs in sorted(leaf.items()):
        r = ",".join(walk(t))
        rng = sorted(bs)
        print(f"  leaf ${t:06x} dx>>4 in {rng[0]:x}..{rng[-1]:x} ({len(rng)} buckets {''.join('%x' % x for x in rng)}): {r}")
    if name == "T1":
        # which sub-states of the target (+47) select which leaf for bucket 0 (and the state byte +46 & $f groups)
        for b in (0, 5):
            p2 = l(p1 + 4 * b)
            rows = {}
            for s in range(16):
                p3 = l(p2 + 4 * s)
                subs = tuple(l(p3 + 4 * k) for k in range(16) if 0x400 <= l(p3 + 4 * k) < 0x2c000)
                rows.setdefault(subs, []).append(s)
            for subs, ss in rows.items():
                print(f"   bucket {b}: target+46&f in {''.join('%x' % x for x in ss)}: index by target+47 -> " + " ".join("%x" % (t & 0xffff) for t in subs))

if __name__ == "__main__":
    ty = int(sys.argv[1], 16)
    names = [a for a in sys.argv[2:] if a in T] or list(T)
    for n in names: dump(ty, n)
