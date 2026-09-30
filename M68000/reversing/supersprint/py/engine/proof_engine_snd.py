"""Differential test of the engine-sound routine $12450(car, speed):
   if -58(A4)[car] != 0 (an effect owns the channel) nothing happens.  rec = -66(A4) + car*30.
   speed > 20 : if rec.level(+8) < 200 + (speed>>3): level += 8 ; rec.period(+2) = 3000 - 4*speed ; rec.interval(+20) = 18 - (speed>>3)
   else       : if rec.level > 130: level -= 8"""
import sys, os, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from calldiff import CallDiff

cd = CallDiff(); R = cd.ram
rec0 = struct.unpack_from('>I', R, A4 - 66)[0]; lev0 = struct.unpack_from('>I', R, A4 - 58)[0]
random.seed(6)
ok = n = 0
for t in range(60):
    car = random.randrange(3); speed = random.choice([0, 5, 20, 21, 40, 80, 100, 130, 200, random.randrange(0, 250)])
    busy = random.choice([0, 0, 0, 2])
    rec = rec0 + car * 30
    level = random.randrange(0, 260); period = random.randrange(0, 4000); interval = random.randrange(0, 30)
    cd.poke_word(lev0 + 2 * car, busy); cd.poke_word(rec + 8, level); cd.poke_word(rec + 2, period); cd.poke_word(rec + 20, interval)
    oc, ch, d = cd.call(0x12450, struct.pack('>hh', car, speed))
    assert oc == 'returned', oc
    g = lambda a: struct.unpack('>h', bytes(cd.apply(cd.ram[a:a + 2], a, ch)))[0]
    got = (g(rec + 8), g(rec + 2), g(rec + 20))
    if busy: want = (level, period, interval)
    elif speed > 20:
        lv = level + 8 if level < 200 + (speed >> 3) else level
        want = (lv, 3000 - 4 * speed, 18 - (speed >> 3))
    else:
        want = (level - 8 if level > 130 else level, period, interval)
    ok += (got == want); n += 1
    if got != want: print('MISMATCH car', car, 'speed', speed, 'busy', busy, 'got', got, 'want', want)
print('engine sound $12450: %d / %d equal' % (ok, n))
cd.close()
