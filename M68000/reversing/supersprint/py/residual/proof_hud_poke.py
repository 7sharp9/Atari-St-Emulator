"""Whole-HUD-band differential with poked state: poke random 6-digit scores (leading blanks = $80) into the staging array -4846(A4) and lap digits
-3906(A4) in a live mid-race snapshot, let the game run ~120k steps (every panel refreshed several times), snapshot, and compare the HUD
band rebuilt by hud_rebuild.rebuild (lap.py $158ea + hud.py $15e5a + captions/icons) with the live stash and screen.  usage: proof_hud_poke.py [trials]"""
import sys, os, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
os.environ['ENGINE_OUT'] = os.path.join(AGENT, 'engine_out')
from common import *
from calldiff import CallDiff
import hud_rebuild as HR
N = int(sys.argv[1]) if len(sys.argv) > 1 else 6
random.seed(5)
tot_px = ok_px = 0; exact = 0
for t in range(N):
    cd = CallDiff(sscfg.SNAP_RACE)
    st = bytearray()
    for car in range(3):
        n = random.randrange(1, 7)                       # number of significant digits
        digs = [random.randrange(10) for _ in range(n)]
        if n > 1 and digs[0] == 0: digs[0] = random.randrange(1, 10)
        st += bytes([0x80] * (6 - n) + digs)
    cd.poke(sscfg.A4 - 4846, bytes(st))
    laps = [random.randrange(8) for _ in range(3)]       # the rank key lap*$2000 wraps at 8
    for car in range(3): cd.poke_word(sscfg.A4 - 3906 + 2 * car, laps[car])
    cd.r.cmd('s 120000')
    out, _ = cd.r.cmd('u 13c4e 400000'); assert any('reached' in l for l in out)      # the rts of $13bbe: the leader-blink rule's hypothesis 0 is exact here
    p = os.path.join(SNAP, 'poke_%d.snap' % t)
    cd.r.cmd('snap %s' % p)
    cd.close()
    R = Ram(p)
    S, info = HR.rebuild(R, 0)
    stash = bytes(R.b[R.g(-86):R.g(-86) + 32000]); draw = bytes(R.b[R.g(-78):R.g(-78) + 32000])
    regs = load_video_regs(p); pal = [st_rgb(w) for w in regs['palette_words']]
    a = decode_st_screen(bytes(S), pal); b = decode_st_screen(stash, pal); c = decode_st_screen(draw, pal)
    pa, pb, pc = a.load(), b.load(), c.load()
    bad = sum(1 for y in range(30) for x in range(320) if pa[x, y] != pb[x, y])
    badc = sum(1 for y in range(30) for x in range(320) if pa[x, y] != pc[x, y])
    tot_px += 9600; ok_px += 9600 - bad
    exact += (bad == 0 and badc == 0)
    print('trial %d scores %s laps %s | latched state %s digits %s | band px differing vs stash %d, vs draw screen %d' % (t, st.hex(), laps, info['state'], info['digits'], bad, badc))
print('HUD band (rows 0..29, 9600 px) rebuilt exact vs live stash+screen in %d / %d poked trials; %d / %d pixels equal' % (exact, N, ok_px, tot_px))
