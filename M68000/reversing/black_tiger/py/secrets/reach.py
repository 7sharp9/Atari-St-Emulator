"""Reachability census over the COMMAND.PRG whole-image listing ($c470..$10786 is code).
Tier A: reached from $c470 by direct control flow (bsr/jsr/jmp/bra/bcc/dbf targets + fallthrough).
Tier B: additionally roots = every instruction address that appears as a 4-byte literal anywhere in the
text segment (immediates, tables) - an over-approximation (may include coincidences).
Prints unreached instruction ranges. Validation: A routine with a known caller must be Tier A."""
import re, os, sys, struct
from btsec import *
LST = os.path.join(WORK, "agents", "systems", "cmd_play.asm")
CODE_LO, CODE_HI = 0xc470, 0x10786
ins = {}   # addr -> (text)
order = []
for l in open(LST):
    m = re.match(r"\s+\$([0-9a-f]+): (.*)", l)
    if not m: continue
    a = int(m.group(1), 16)
    if a > CODE_HI: break
    ins[a] = m.group(2).strip(); order.append(a)
nxt = {order[i]: order[i+1] for i in range(len(order)-1)}
def targets(t):
    r = []
    m = re.search(r"== \$([0-9a-f]+)", t)
    if m: r.append(int(m.group(1), 16))
    mn = t.split()[0]
    if mn in ("bsr","bra") or re.match(r"b(cc|cs|eq|ne|ge|gt|hi|le|ls|lt|mi|pl|vc|vs)$", mn):
        m = re.match(r"\S+ \$([0-9a-f]+)$", t)
        if m: r.append(int(m.group(1), 16))
    if mn in ("jsr","jmp"):
        m = re.match(r"\S+ \$([0-9a-f]+)(?:\.l)?$", t)
        if m: r.append(int(m.group(1), 16))
    return r
def terminal(t):
    mn = t.split()[0]
    return mn in ("rts","rte","rtr","bra","jmp") or t.startswith("???")
def walk(roots):
    seen = set(); st = list(roots)
    while st:
        a = st.pop()
        while a in ins and a not in seen:
            seen.add(a); t = ins[a]
            for x in targets(t): st.append(x)
            if terminal(t): break
            a = nxt.get(a)
            if a is None: break
    return seen
A = walk([0xc470])
mem = ram(os.path.join(WORK, "play_start.snap"))
roots = set()
for lo in range(0xc470, 0x1f274):
    v = struct.unpack(">I", bytes(mem[lo:lo+4]))[0]
    if v in ins and CODE_LO <= v < CODE_HI: roots.add(v)
B = walk(set([0xc470]) | roots)
def ranges(sel):
    out = []; cur = None
    for a in order:
        if a in sel:
            if cur and nxt_ok(cur[1], a): cur[1] = a
            else:
                cur = [a, a]; out.append(cur)
        else: cur = None
    return out
def nxt_ok(prev, a): return nxt.get(prev) == a
if __name__ == "__main__":
    import json
    un = set(order) - B
    print("instructions", len(order), "tierA", len(A), "tierB", len(B), "unreached", len(un))
    print("== unreached ranges (addr range, n, first ins)")
    for lo, hi in ranges(un):
        n = sum(1 for a in order if lo <= a <= hi)
        print("%06x-%06x %4d  %s" % (lo, hi, n, ins[lo]))
    print("== tier B only (literal-rooted), ranges")
    onlyB = B - A
    for lo, hi in ranges(onlyB):
        n = sum(1 for a in order if lo <= a <= hi)
        print("%06x-%06x %4d  %s" % (lo, hi, n, ins[lo]))
