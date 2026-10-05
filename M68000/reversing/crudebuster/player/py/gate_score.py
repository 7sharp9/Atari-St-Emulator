"""gate_score.py <hit.txt> [thrown]: score awarded per hit/kill versus the ROM table ($24952 by pool A type, $4016 BCD points), from lua/hitlab.lua output.
   hit.txt lines: trial type t field old>new (hex; the score is BCD).  jab mode: each non-lethal hit gives 'hit' points, the killing hit 'kill' points (-1 HP per jab hit).
   'thrown' mode (button b3 run): the throw kills (HP-4) and gives 'thrown' points."""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from romlib import *
SCORE = [int("%x" % l(0x4016 + 4 * i)) for i in range(24)]
pts = lambda t, k: (lambda x: SCORE[x - 1] if x else 0)(b(0x24952 + 4 * t + k))
mode = sys.argv[2] if len(sys.argv) > 2 else "jab"
tr = collections.OrderedDict()
for ln in open(sys.argv[1]):
    f = ln.split(); trial, t, tt, field, ch = int(f[0]), int(f[1], 16), int(f[2]), f[3], f[4]
    tr.setdefault(trial, {"type": t, "ev": []})["ev"].append((tt, field, [int(x, 16) for x in ch.split(">")]))
ok = bad = skipped = 0
for k, d in tr.items():
    t = d["type"]; ev = d["ev"]
    hp0 = next((e[2][1] for e in ev if e[1] == "hp" and e[0] == 1), 0)
    died = any(e[1] == "st" and e[2][1] in (2, 4) for e in ev)
    bcd = lambda v: int("%x" % v)
    inc = [bcd(e[2][1]) - bcd(e[2][0]) for e in ev if e[1] == "sc" and e[0] > 1]
    gone = set(e[0] for e in ev if e[1] == "act" and e[2][1] == 0)   # the lab clears the record at trial end: ignore that frame
    hpf = [e[2][1] for e in ev if e[1] == "hp" and e[0] not in gone][-1]
    if mode == "jab":
        if hpf == hp0: skipped += 1; print("trial %d type %02x: no jab landed (hp %d), skipped" % (k, t, hp0)); continue
        exp = [pts(t, 0)] * (hp0 - 1) + [pts(t, 2)] if died else [pts(t, 0)] * (hp0 - hpf)
    else:
        if not died: skipped += 1; print("trial %d type %02x: not grabbed/killed, skipped" % (k, t)); continue
        exp = [pts(t, 1)]
    good = inc == exp
    ok += good; bad += (not good)
    print("trial %d type %02x hp %d: score increments %s expected %s %s" % (k, t, hp0, inc, exp, "OK" if good else "MISMATCH"))
print("trials matching the ROM table: %d, mismatching: %d, skipped: %d" % (ok, bad, skipped))
