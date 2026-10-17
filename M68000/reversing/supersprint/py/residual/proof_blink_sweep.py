"""Leader-blink sweep at exact points of the HUD driver: poke lap digits so that car L leads (laps[L] = 6; the rank key is a 16-bit sum
lap*$2000 + ..., so 8 or more would wrap), then for 40 consecutive frames snapshot at the ENTRY of $13bbe (before this frame's panel refresh) and at its RTS $13c4e (after it).
For each snapshot compare (a) the blank panels of the live stash with blink.predict (hypothesis 1 at entry: the last refresh ran at ph = (f-1)%6; hypothesis 0 at the rts: ph = f%6),
(b) the whole HUD band rebuilt with that rule against the live stash.  usage: proof_blink_sweep.py [leader car ...]"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
os.environ['ENGINE_OUT'] = os.path.join(AGENT, 'engine_out')
from common import *
from calldiff import CallDiff
import hud_rebuild as HR, blink
leaders = [int(a) for a in sys.argv[1:]] or [0, 1, 2]
tb = tt = tp = tpt = 0
os.path.exists(os.path.join(SNAP, "sweep_tmp.snap")) and os.remove(os.path.join(SNAP, "sweep_tmp.snap"))
for L in leaders:
    cd = CallDiff(sscfg.SNAP_RACE)
    laps = [1, 1, 1]; laps[L] = 6
    for car in range(3): cd.poke_word(sscfg.A4 - 3906 + 2 * car, laps[car])
    for i in range(40):
        for where, addr, hyp in (('entry', '13bbe', 1), ('rts', '13c4e', 0)):
            out, _ = cd.r.cmd('u %s 400000' % addr); assert any('reached' in l for l in out), out[:3]
            p = os.path.join(SNAP, 'sweep_tmp.snap'); cd.r.cmd('snap %s' % p)
            R = Ram(p)
            ob = blink.observed_blank(R); pr = blink.predict(R, hyp)
            S, info = HR.rebuild(R, 0, blank=pr)
            stash = bytes(R.b[R.g(-86):R.g(-86) + 32000])
            regs = load_video_regs(p); pal = [st_rgb(w) for w in regs['palette_words']]
            a = decode_st_screen(bytes(S), pal); b = decode_st_screen(stash, pal); pa, pb = a.load(), b.load()
            bad = sum(1 for y in range(30) for x in range(320) if pa[x, y] != pb[x, y])
            tb += (ob == pr); tt += 1; tp += 9600 - bad; tpt += 9600
            print('leader %d frame %2d %-5s f=%d cyc=%d lead=%d observed %s predicted %s %s band px differing %d' % (L, i, where, R.gw(-8072), R.gsw(-4814), R.gsw(-4812), ob, pr, 'OK ' if ob == pr else 'BAD', bad))
            cd.r.cmd('s 1')
    cd.close()
print('blank-panel prediction equal in %d / %d snapshots; HUD band pixels equal %d / %d' % (tb, tt, tp, tpt))
