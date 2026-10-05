"""handler_summary.py [pool]: per distinct handler of pool B (default) / C, a feature summary from the linear listing.
Range = [handler start, next distinct handler start). Features: call targets, spawn types (D6 before $21efa/$21e72/$21eb6),
sound ids (D7 before $e1c), player-record refs, flag writes, destroy calls ($2250c)."""
import re, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from cbrom import *
pool = sys.argv[1] if len(sys.argv) > 1 else "B"
tab, n = {"A": (0x10418, 80), "B": (0x10558, 84), "C": (0x106c8, 44)}[pool]
H = [L(tab + 4*i) for i in range(n)]
types_of = {}
for i, h in enumerate(H): types_of.setdefault(h, []).append(i)
starts = sorted(types_of)
import subprocess
ROMP = os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin")
PYX = os.path.join(root, ".venv/bin/python")
def ins(a, b):
    out = []
    txt = subprocess.run([PYX, os.path.join(root, "tools/disassemble.py"), "--rom", ROMP, "--base", "0", "--linear", "%x" % a, str((b - a) // 2 + 2)], capture_output=True, text=True).stdout
    for l in txt.split("\n"):
        m = re.match(r"\s+\$([0-9a-f]+):\s+(.*)", l)
        if not m: continue
        ad = int(m.group(1), 16)
        if ad >= b: break
        out.append((ad, m.group(2)))
    return out
for k, s in enumerate(starts):
    e = starts[k+1] if k+1 < len(starts) else s + 0x400
    L_ = ins(s, e)
    calls, sp, snd, plr, fl, dst = {}, [], [], set(), set(), 0
    d6 = d7 = None
    for ad, t in L_:
        mm = re.match(r"(?:moveq|move\.[bwl]) #(\$?-?[0-9a-f]+),D6\b", t)
        if mm: d6 = mm.group(1)
        mm = re.match(r"(?:moveq|move\.[bwl]) #(\$?-?[0-9a-f]+),D7\b", t)
        if mm: d7 = mm.group(1)
        mm = re.match(r"(jsr|bsr)\s+(\S+)", t)
        if mm:
            tg = mm.group(2); m2 = re.search(r"== \$([0-9a-f]+)", t)
            if m2: tg = "$" + m2.group(1)
            tg = tg.replace(".l", "").replace(".w", "")
            calls[tg] = calls.get(tg, 0) + 1
            if tg in ("$21efa", "$21e72", "$21eb6"): sp.append((tg, d6, d7))
            if tg in ("$e1c",): snd.append(d7)
            if tg == "$2250c": dst += 1
        for mm in re.finditer(r"\$(80[0-9a-f]{3})\.l", t):
            a = int(mm.group(1), 16)
            if 0x80100 <= a < 0x80200: plr.add("%x" % a)
            elif a in (0x80040, 0x80041, 0x80400, 0x8005a, 0x8005c, 0x80014, 0x80015): 
                if re.match(r"(bset|bclr|move|clr|or|and|add|sub)", t): fl.add("%s:%x" % (t.split()[0], a))
    print("handler %x types %s  [%x..%x) %d insns" % (s, types_of[s], s, e, len(L_)))
    print("   calls:", " ".join("%s%s" % (k_, "x%d" % v if v > 1 else "") for k_, v in sorted(calls.items())))
    if sp: print("   spawns:", sp)
    if snd: print("   sounds D7:", snd)
    if plr: print("   player refs:", sorted(plr))
    if fl: print("   flag writes:", sorted(fl))
