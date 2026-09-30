"""Compare sfx_engine.py against the live YM register-write log for sound indices.  usage: sfx_check.py idx [idx ...]  (all 1..52 with 'all')"""
import sys, json, struct
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from sfx_live import *
from sfx_engine import Engine

def vbl_groups(regs):
    """a VBL group = writes from reg 7 (start of $1d1d0) up to the next reg 7; hw-envelope setup writes (13,11,12) come before reg 7."""
    gs = []; cur = []
    for step, pc, reg, val in regs:
        if pc < 0x1d1f0 and pc >= 0x1d160:      # $1d162.. hw envelope setup inside $1d0f2
            cur.append((reg, val)); continue
        if reg == 7 and any(r == 7 for r, _ in cur):
            gs.append(cur); cur = []
        cur.append((reg, val))
    if cur: gs.append(cur)
    return gs

def check(idx, steps=4000000, verbose=False):
    r, log, st = live(idx, steps)
    regs = groups(log)
    r.close()
    live_groups = vbl_groups(regs)
    ram_ = ram(SNAP)
    best = None
    for off in (0, 1, 2, 3):
        e = Engine(ram_)
        voice = e.start(idx)
        ok = tot = 0; first_bad = None
        for k in range(off, len(live_groups) - 1):
            pred = e.vbl()
            got = live_groups[k]
            flagged = any(v.flags & 2 for v in e.v)
            for (pr, pv), (gr, gv) in zip(pred, got):
                if pr == 6 and not flagged: continue
                tot += 1
                if (pr, pv) == (gr, gv): ok += 1
                elif first_bad is None: first_bad = (k, pred, got)
            if len(pred) != len(got):
                if first_bad is None: first_bad = (k, 'len', pred, got)
        cand = (ok, tot, off, first_bad, voice)
        if best is None or (tot and ok / tot > best[0] / max(best[1], 1)): best = cand
    ok, tot, off, fb, voice = best
    return dict(idx=idx, voice=voice, live_vbls=len(live_groups), align=off, ok=ok, tot=tot, first_bad=fb)

if __name__ == '__main__':
    args = sys.argv[1:]
    ids = list(range(1, 53)) if args == ['all'] else [int(a, 0) for a in args]
    for i in ids:
        res = check(i)
        print(json.dumps(res, default=str))
        sys.stdout.flush()
