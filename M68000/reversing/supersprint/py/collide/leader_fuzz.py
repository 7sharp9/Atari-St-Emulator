"""leader_fuzz.py - proves what $13b34 computes: the index of the car with the largest 16-bit progress key
   key_i = (laps_i << 13) + (sector_i << 10) + tripwire_i   (laps -3906, sector -3850, tripwire -3842; all 16-bit wrap),
   ties go to the lowest index (a later car must be strictly greater).  Random 4-car vectors (including forced ties) are poked into
   the arrays of a live snapshot, then callcap $13b34 and compare D0.w with this model.
   usage: leader_fuzz.py <snap> [n=300] [seed]"""
import sys, os, random
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import pl
pl.OUT = os.path.join(pl.sscfg.WORK, 'agents', 'collide')
from difflib_ss import *
snap = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 300; rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
h = Harness(snap); h.run_to(0xdf18, 1, 8000000)

def model(laps, sec, trip):
    keys = [(((laps[i] << 13) + (sec[i] << 10) + trip[i]) & 0xffff) for i in range(4)]
    best = 0
    for i in range(1, 4):
        if keys[best] < keys[i]: best = i
    return best

ok = 0; byidx = [0] * 4; ties = 0; bad = []
for t in range(n):
    laps = [rng.randint(0, 4) for _ in range(4)]; sec = [rng.randint(0, 5) for _ in range(4)]; trip = [rng.choice([0, 1, 2, 3, 7, 20, 99, 400]) for _ in range(4)]
    if t % 5 == 0:                       # force a full tie between two cars
        a, b = rng.sample(range(4), 2); laps[b], sec[b], trip[b] = laps[a], sec[a], trip[a]
    if t % 7 == 0:
        trip = [rng.randint(0, 3) for _ in range(4)]; sec = [2] * 4; laps = [1] * 4          # decided by the tripwire counts alone
    pl.poke_arr(h, -3906, laps); pl.poke_arr(h, -3850, sec); pl.poke_arr(h, -3842, trip)
    d, j, o = h.callcap(0x13b34)
    got = j['regN'][0] & 0xffff
    want = model(laps, sec, trip)
    keys = [(((laps[i] << 13) + (sec[i] << 10) + trip[i]) & 0xffff) for i in range(4)]
    if keys.count(max(keys)) > 1: ties += 1
    if got == want: ok += 1; byidx[want] += 1
    elif len(bad) < 5: bad.append((laps, sec, trip, got, want))
print('%s: $13b34 == model in %d/%d (winners by index %s, %d with a tied maximum); mismatches: %s' % (os.path.basename(snap), ok, n, byidx, ties, bad))
h.close()
