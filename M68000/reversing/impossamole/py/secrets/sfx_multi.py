"""Voice rotation: trigger four different effects ~5 game frames apart (all three voices busy for the fourth) and compare with the model, which
allocates voices round-robin ($1cc79 bits 0-1, bits 4-6 = locked voices) exactly like $1c8e2.  The VBL index of each start is searched (0-10 VBLs after the previous)."""
import sys, itertools
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from sfx_live import *
from sfx_check import vbl_groups
from sfx_engine import Engine
SEQ = [9, 20, 12, 36]
def run_live(seq, gap_steps=60000, tail=1500000):
    r = Repl(SNAP); install(r); r.cmd('s 30000'); r.cmd('watch ff8800 4')
    for i in seq:
        trigger(r, i); r.cmd(f's {gap_steps}')
    r.cmd(f's {tail}')
    log = parse(r.err); r.close()
    return vbl_groups(groups(log))
def model(seq, starts, n):
    e = Engine(ram(SNAP)); voices = []; out = []
    for k in range(n):
        for j, s in enumerate(starts):
            if s == k: voices.append(e.start(seq[j]))
        out.append(e.vbl())
    return out, voices
def score(pred, live, off):
    ok = tot = 0
    for k in range(len(pred)):
        if k + off >= len(live) - 1: break
        for (a, b), (c, d) in zip(pred[k], live[k + off]):
            if a == 6: continue
            tot += 1; ok += ((a, b) == (c, d))
        tot += abs(len(pred[k]) - len(live[k + off]))
    return ok, tot
if __name__ == '__main__':
    live = run_live(SEQ)
    n = len(live) - 4
    best = None
    # brute-force the start VBLs: s0 = 0 (alignment offset off), s1..s3 increasing
    for off in (0, 1, 2):
        s0 = 0
        for s1 in range(1, 9):
            for s2 in range(s1 + 1, s1 + 9):
                for s3 in range(s2 + 1, s2 + 9):
                    pred, v = model(SEQ, [s0, s1, s2, s3], 60)
                    ok, tot = score(pred, live, off)
                    if best is None or ok / max(tot, 1) > best[0] / max(best[1], 1) or (ok == tot and best[0] != best[1]):
                        best = (ok, tot, off, (s0, s1, s2, s3), v)
    print('best alignment: ok %d / tot %d, live offset %d, start VBLs %s, voices used %s' % best)
