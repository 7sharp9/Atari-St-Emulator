"""adis.py <start> <end> : 68000 disassembly of [start,end) with computed-jump tables decoded.
A `lea N(PC) == $T,A0` (or `lea $T.w/.l,A0`) followed within 8 instructions by `movea.l 0(A0,Dn.w),A1` / `jsr (A1)` or `jmp`
marks $T as a table of longword code addresses (read while each value lies in $0600-$2c400 and is even); the table is printed as
`TABLE $T: a0 a1 ...` and disassembly resumes after it. Tables whose first entry is not code are left alone."""
import re, subprocess, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from cbrom import *
PYX = os.path.join(root, ".venv/bin/python")
ROMP = os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin")
def dis(a, n):
    txt = subprocess.run([PYX, os.path.join(root, "tools/disassemble.py"), "--rom", ROMP, "--base", "0", "--linear", "%x" % a, str(n)], capture_output=True, text=True).stdout
    out = []
    for l in txt.split("\n"):
        m = re.match(r"\s+\$([0-9a-f]+):\s+(.*)", l)
        if m: out.append((int(m.group(1), 16), m.group(2)))
    return out
def adis(start, end, tables=None):
    res = []; pos = start; tables = tables if tables is not None else []
    while pos < end:
        ins = dis(pos, min(400, (end - pos) // 2 + 2))
        cut = None
        for i, (a, t) in enumerate(ins):
            if a >= end: break
            res.append((a, t))
            m = re.match(r"lea (?:-?\d+\(PC\) == |)\$([0-9a-f]+)(?:\.[wl])?,A0", t)
            if m:
                tb = int(m.group(1), 16)
                ctx = " ".join(x[1] for x in ins[i+1:i+9])
                if re.search(r"movea\.l 0\(A0,D\d\.(w|l)\),A\d", ctx) and (tb % 2 == 0) and tb > a and tb < end + 0x400 and tb not in [x[0] for x in tables]:
                    ents = []
                    p = tb
                    while p < tb + 4 * 64:
                        v = L(p)
                        if v % 2 == 0 and 0x600 <= v < 0x2c400: ents.append(v); p += 4
                        else: break
                    if len(ents) >= 2:
                        tables.append((tb, ents))
        # find the earliest table start within this chunk that lies ahead of the code printed so far; cut there
        pend = [t for t in tables if t[0] >= pos and t[0] < (ins[-1][0] if ins else end) + 1 and not any(x[0] == t[0] and x[1].startswith('TABLE') for x in res)]
        if pend:
            tb, ents = min(pend)
            res = [(a, t) for (a, t) in res if a < tb]
            res.append((tb, "TABLE $%x: %s" % (tb, " ".join("%x" % e for e in ents))))
            pos = tb + 4 * len(ents)
        else:
            break
    return res
if __name__ == "__main__":
    s, e = int(sys.argv[1], 16), int(sys.argv[2], 16)
    for a, t in adis(s, e): print("  $%06x: %s" % (a, t))
