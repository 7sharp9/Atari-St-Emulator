"""Condensed view of the shared AI chooser `$2438a` for a pool A type: for each table (T1 same level, T2 enemy far below target, T3 enemy above target)
and each dx bucket, the distribution of states the chosen routine can start (a routine is either a start routine that sets `move.b #N,3(A6)`, or a
chooser `btst #7,1(A6) / $ea44 & 3 / table of 4 start routines`: 4 equally likely outcomes, only taken when the animation has wrapped (+1 bit 7)).
usage: ai_summary.py <type hex>"""
import os, sys, re
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(here, "../../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
lin = {}
for line in open(os.path.join(root, "scratchpad/crudebuster/all_lin.txt")):
    a, _, ins = line.strip().partition(": ")
    lin[int(a[1:], 16)] = ins
def l(a): return int.from_bytes(rom[a:a + 4], "big")
def ok(a): return 0x400 <= a < 0x2c000
T = {"T1": 0x24508, "T2": 0x24644, "T3": 0x24780}
def states_of(addr, depth=0):
    """returns dict state -> probability (None key = no state change/unknown)"""
    out = {}
    a = addr
    seen = 0
    chooser = None
    while seen < 40:
        ins = lin.get(a)
        if ins is None: break
        m = re.match(r"move\.b #\$([0-9a-f]+),3\(A6\)", ins)
        if m:
            return {int(m.group(1), 16): 1.0}
        m = re.match(r"lea (-?\d+)\(PC\) == \$([0-9a-f]+),A0", ins)
        if m and chooser is None and "jsr $ea44.l" in " ".join(lin.get(a - k, "") for k in (2, 4, 6, 8, 10, 12)):
            tb = int(m.group(2), 16)
            res = {}
            for i in range(4):
                for s, p in states_of(l(tb + 4 * i), depth + 1).items(): res[s] = res.get(s, 0) + p / 4
            return res
        m = re.match(r"jsr (-?\d+)\(PC\) == \$([0-9a-f]+)$", ins) or re.match(r"jsr \$([0-9a-f]+)\.l", ins)
        if m and ("(PC)" in ins) and depth < 4:
            tgt = int(m.group(2), 16)
            if 0x22000 <= tgt < 0x22d00 or tgt in (0x22c2c, 0x2280c): pass
            else:
                r = states_of(tgt, depth + 1)
                if r: return r
        if ins.startswith("rts"): break
        a += 2
        while a not in lin and seen < 40: a += 2; seen += 1
        seen += 1
    return {None: 1.0}
def fmt(d): return " ".join(f"s{('?' if s is None else format(s, 'x'))}:{p:.2f}" for s, p in sorted(d.items(), key=lambda x: (x[0] is None, x[0] or 0)))
ty = int(sys.argv[1], 16)
def rng(ix):
    out, i = [], 0
    ix = sorted(ix)
    while i < len(ix):
        j = i
        while j + 1 < len(ix) and ix[j + 1] == ix[j] + 1: j += 1
        out.append(format(ix[i], "x") if i == j else f"{ix[i]:x}-{ix[j]:x}")
        i = j + 1
    return ",".join(out)
for name in ("T1", "T2", "T3"):
    p1 = l(T[name] + 4 * ty)
    print(f"== type {ty:02x} {name}")
    rows = []
    for b in range(16):
        p2 = l(p1 + 4 * b)
        if name == "T1":
            groups = {}
            for s_ in range(16):
                p3 = l(p2 + 4 * s_)
                subs = []
                for k in range(16):
                    t = l(p3 + 4 * k)
                    if not ok(t): break
                    subs.append(t)
                groups.setdefault(tuple(subs), []).append(s_)
            parts = []
            for subs, ss in groups.items():
                uniq = {}
                for i, t in enumerate(subs): uniq.setdefault(t, []).append(i)
                desc = "; ".join(f"tgt+47 in {rng(ix)}: " + fmt(states_of(t)) for t, ix in uniq.items())
                parts.append(f"tgt+46&f in {rng(ss)} -> {desc}")
            rows.append((b, " || ".join(parts)))
        else:
            rows.append((b, fmt(states_of(p2))))
    i = 0
    while i < len(rows):
        j = i
        while j + 1 < len(rows) and rows[j + 1][1] == rows[i][1]: j += 1
        print(f"  dx>>4={rows[i][0]:x}" + (f"-{rows[j][0]:x}" if j > i else "") + f": {rows[i][1]}")
        i = j + 1
