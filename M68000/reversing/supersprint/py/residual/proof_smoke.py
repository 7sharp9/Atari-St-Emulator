"""Differential test (callcap vs smoke.py) of the smoke-puff spawner $b6f8, updater $afc6 and (inside it) the puff blitter $143ca.
Random slot states (x, y, frame, end, tick), random headings/positions; compares the screen (32000 B) and the whole smoke state region
(A4-4700 .. A4-4540) after one $afc6 call, and after one $b6f8 call.  usage: proof_smoke.py [trials]"""
import sys, os, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
os.environ['ENGINE_OUT'] = os.path.join(AGENT, 'engine_out')
from common import *
from calldiff import CallDiff
import smoke
N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read(); b5 = bytes(dat[132566:132566 + 30000])
cd = CallDiff(); R = cd.ram
scr = struct.unpack_from('>I', R, A4 - 78)[0]
random.seed(3)
LO, HI = A4 - 4700, A4 - 4540
okS = okR = nS = nR = 0; okS2 = okR2 = nS2 = nR2 = 0
exact_u = exact_s = 0
for t in range(N):
    # ---- $afc6 ----
    for i in range(8):
        live = random.random() < 0.7
        cd.poke_word(A4 - 4598 + 4 * i, random.randrange(4, 300) if live else 0)
        cd.poke_word(A4 - 4596 + 4 * i, random.randrange(0, 190))
        end = random.randrange(5, 45)
        cd.poke_word(A4 - 4614 + 2 * i, random.choice([random.randrange(0, 44), end, end - 1, 0x28, 0x29, 0x2A]))
        cd.poke_word(A4 - 4630 + 2 * i, end)
        cd.poke_word(A4 - 4646 + 2 * i, random.choice([0, 1, 2, 3, 3, 3, 4]))
    par = random.randrange(2); cd.poke_word(A4 - 8072, par)
    m = bytearray(cd.ram)
    oc, ch, d = cd.call(0xAFC6, presets='A5=a304 A4=1eb44')
    if oc != 'returned':
        print('FAIL', oc, [(i, bytes(cd.ram[A4-4598+4*i:A4-4598+4*i+4]).hex(), bytes(cd.ram[A4-4614+2*i:A4-4614+2*i+2]).hex(), bytes(cd.ram[A4-4630+2*i:A4-4630+2*i+2]).hex(), bytes(cd.ram[A4-4646+2*i:A4-4646+2*i+2]).hex()) for i in range(8)], 'par', par); raise SystemExit(1)
    smoke.update(m, b5, par, scr)
    liveS = cd.apply(R[scr:scr + 32000], scr, ch); liveR = cd.apply(R[LO:HI], LO, ch)
    eS = sum(a == b for a, b in zip(liveS, m[scr:scr + 32000])); eR = sum(a == b for a, b in zip(liveR, m[LO:HI]))
    okS += eS; nS += 32000; okR += eR; nR += HI - LO; exact_u += (eS == 32000 and eR == HI - LO)
    if eS != 32000 or eR != HI - LO: print('  $afc6 trial', t, 'screen', eS, 'state', eR)
    cd.ram[:] = bytearray(cd.ram)  # (cd.ram already holds the pokes; the call itself is rolled back by callcap)
    # ---- $b6f8(car, p) ----
    car = random.randrange(4); p = random.randrange(0, 4000)
    cd.poke_word(A4 - 3690 + 2 * car, random.randrange(0, 300)); cd.poke_word(A4 - 3698 + 2 * car, random.randrange(0, 190)); cd.poke_word(A4 - 3706 + 2 * car, random.randrange(16))
    m = bytearray(cd.ram)
    oc, ch, d = cd.call(0xB6F8, struct.pack('>HH', car, p), presets='A5=a304 A4=1eb44')
    assert oc == 'returned', oc
    smoke.spawn(m, car, p)
    liveR = cd.apply(R[LO:HI], LO, ch)
    eR = sum(a == b for a, b in zip(liveR, m[LO:HI])); okR2 += eR; nR2 += HI - LO; exact_s += (eR == HI - LO)
    if eR != HI - LO: print('  $b6f8 trial', t, 'car', car, 'state', eR)
print('$afc6 updater+blitter: screen %d/%d bytes, state %d/%d bytes equal; %d/%d trials exact' % (okS, nS, okR, nR, exact_u, N))
print('$b6f8 spawner: state %d/%d bytes equal; %d/%d trials exact' % (okR2, nR2, exact_s, N))
cd.close()
