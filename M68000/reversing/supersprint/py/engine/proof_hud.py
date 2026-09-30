"""Differential test of the HUD big-digit routine $15e5a against hud.py (screen, stash and depth-layer bytes)."""
import sys, os, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from calldiff import CallDiff
from hud import *

cd = CallDiff(); R = cd.ram
dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
b7 = dat[165566:165566 + 3520]
def g(off): return struct.unpack_from('>I', R, A4 + off)[0]
scr = g(-78); stash = g(-86); layer = g(-94) + 0x3E80; bgb = g(-4940)
assert bytes(R[g(-4936):g(-4936) + 3520]) == b7, 'B7 in RAM differs from SUPER.DAT'
random.seed(4)
okS = okT = okL = 0; N = 30
for t in range(N):
    car = random.randrange(3); digit = random.randrange(10)
    par = random.randrange(2)
    cd.poke_word(A4 - 8072, par)                       # frame parity: even -> the routine first copies -3906[car] into -4822[car]
    cd.poke_word(A4 - 3906 + 2 * car, digit); cd.poke_word(A4 - 4822 + 2 * car, (digit + 3) % 10)
    bgdata = bytes(random.randrange(256) for _ in range(0x90 + 11 * 160 + 16))
    cd.poke(bgb, bgdata)
    use = digit if par == 0 else (digit + 3) % 10
    oc, ch, d = cd.call(0x15E5A, struct.pack('>IH', scr, car))
    assert oc == 'returned', oc
    liveS = cd.apply(R[scr:scr + 32000], scr, ch); liveT = cd.apply(R[stash:stash + 32000], stash, ch); liveL = cd.apply(R[layer:layer + 0x300], layer, ch)
    S = bytearray(R[scr:scr + 32000]); T = bytearray(R[stash:stash + 32000]); L = bytearray(R[layer:layer + 0x300])
    draw_digit(S, T, L, bytes(R[bgb:bgb + len(bgdata)]), digit_rows(b7, use), car)
    badS = [i for i, (a, b) in enumerate(zip(liveS, S)) if a != b]
    if badS: print('  trial', t, 'car', car, 'digit', use, 'mismatch screen bytes', len(badS), 'first', badS[:6], [hex(liveS[i]) for i in badS[:6]], [hex(S[i]) for i in badS[:6]])
    okS += sum(a == b for a, b in zip(liveS, S)); okT += sum(a == b for a, b in zip(liveT, T)); okL += sum(a == b for a, b in zip(liveL, L))
print('$15e5a HUD digit: screen %d/%d, stash %d/%d, depth-layer %d/%d bytes equal over %d trials' % (okS, N * 32000, okT, N * 32000, okL, N * 0x300, N))
cd.close()
