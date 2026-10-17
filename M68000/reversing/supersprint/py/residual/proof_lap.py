"""Differential test of the lap-panel composer $158ea against lap.py: random 6-byte digit states (digits 0..9 or blank >= $80, independently
for the staging array -4846(A4) and the latched array -4870(A4)), random frame parity, random pristine background, all three cars.
Compares screen (32000 B), stash (32000 B), depth layer (0x300 B) and the 18-byte state array.  usage: proof_lap.py [trials]"""
import sys, os, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
from common import Ram, A4
from calldiff import CallDiff
import lap

N = int(sys.argv[1]) if len(sys.argv) > 1 else 36
cd = CallDiff(); R = cd.ram
dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read(); b7 = dat[165566:165566 + 3520]
def g(off): return struct.unpack_from('>I', R, A4 + off)[0]
scr = g(-78); stash = g(-86); layer = g(-94); bgb = g(-4940)
assert bytes(R[g(-4936):g(-4936) + 3520]) == b7
blank44 = bytes(R[A4 - 4988:A4 - 4988 + 44]); blank88 = bytes(R[A4 - 5076:A4 - 5076 + 88])
print('blank44', blank44.hex(' ')[:60], '...'); print('blank88', blank88.hex(' ')[:60], '...')
random.seed(11)
def rstate():
    return bytes(random.choice([random.randrange(10)] * 3 + [0x80 + random.randrange(0x80)]) for _ in range(18))
tot = dict(scr=0, stash=0, lay=0, st=0); n = dict(scr=0, stash=0, lay=0, st=0); trials_ok = 0
for t in range(N):
    car = t % 3 if t < 12 else random.randrange(3)
    par = random.randrange(2)
    cd.poke_word(A4 - 8072, par)
    new = rstate(); old = rstate()
    cd.poke(A4 - 4846, new); cd.poke(A4 - 4870, old)
    bgdata = bytes(random.randrange(256) for _ in range(0x90 + 11 * 160 + 32))
    cd.poke(bgb, bgdata)
    oc, ch, d = cd.call(0x158EA, struct.pack('>IH', scr, car))
    assert oc == 'returned', oc
    liveS = cd.apply(R[scr:scr + 32000], scr, ch); liveT = cd.apply(R[stash:stash + 32000], stash, ch); liveL = cd.apply(R[layer:layer + 0x4200], layer, ch)
    liveST = cd.apply(R[A4 - 4870:A4 - 4852], A4 - 4870, ch)
    st = bytearray(old)
    if par == 0: st[6 * car:6 * car + 6] = new[6 * car:6 * car + 6]
    S = bytearray(R[scr:scr + 32000]); T = bytearray(R[stash:stash + 32000]); L = bytearray(R[layer:layer + 0x4200])
    lap.draw(S, T, L, bgdata, b7, blank44, blank88, bytes(st), car)
    bs = sum(a != b for a, b in zip(liveS, S)); bt = sum(a != b for a, b in zip(liveT, T)); bl = sum(a != b for a, b in zip(liveL, L)); bst = sum(a != b for a, b in zip(liveST, st))
    if bs or bt or bl or bst: print('  trial', t, 'car', car, 'par', par, 'state', bytes(st).hex(), 'mismatch screen/stash/layer/state', bs, bt, bl, bst)
    else: trials_ok += 1
    tot['scr'] += 32000 - bs; tot['stash'] += 32000 - bt; tot['lay'] += 0x4200 - bl; tot['st'] += 18 - bst
print('$158ea lap panel: screen %d/%d, stash %d/%d, depth layer %d/%d, state %d/%d bytes equal; %d/%d trials exact' %
      (tot['scr'], N * 32000, tot['stash'], N * 32000, tot['lay'], N * 0x4200, tot['st'], N * 18, trials_ok, N))
cd.close()
