"""dmg_check.py <dmg.txt> [difficulty index 0..3]: compare each logged player-health decrement (pc, old, new) with the damage tables read from the ROM.
   $fc9e writer ($fc34, melee): expected 4 * diff_table[idx][enemy type]  (tables $fd2a $fcca $fd5a $fd8a, chosen by (DSW $80054 & $c)/4)
   $f76e writer ($f700, contact): expected $f78e[type]     $1010a ($100b2): expected $10122[type]"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from romlib import *
fn = sys.argv[1]; di = int(sys.argv[2]) if len(sys.argv) > 2 else 0
tab = [l(0xfcba + 4 * i) for i in range(4)][di]
exp = {0xfc9e: lambda t: (4 * b(tab + t)) & 0xff, 0xf76e: lambda t: b(0xf78e + t), 0x1010a: lambda t: b(0x10122 + t)}
ok = bad = 0; other = collections.Counter(); rows = []
for ln in open(fn):
    f = ln.split(); trial, t, v, fr, pc, old, new = f[:7]; t = int(f[7], 16) if len(f) > 7 else int(t, 16); pc = int(pc, 16); old = int(old, 16); new = int(new, 16)
    if old <= new: continue
    d = old - new
    if pc in exp:
        e = exp[pc](t)
        e = min(e, old)  # clamped at 0
        if d == e: ok += 1
        else: bad += 1; rows.append("MISMATCH type %02x pc %x damage %d expected %d (old %d)" % (t, pc, d, e, old))
    else: other[pc] += 1; rows.append("other writer pc %x type %02x damage %d" % (pc, t, d))
print("decrements matching the ROM tables: %d, mismatching: %d, other writers: %s" % (ok, bad, dict(other)))
for r in [x for x in rows if x.startswith("MISMATCH")] + [x for x in rows if not x.startswith("MISMATCH")][:6]: print(r)
