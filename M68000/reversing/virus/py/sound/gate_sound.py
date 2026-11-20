"""Gate: the Python model (ymmodel.py) against the emulator's own Sound_Trigger/Sound_Tick, run as subroutines
through stserver from f1.snap.  Usage: gate_sound.py [flaw]   (flaw: shift2 | nonmax | prio_ge, the broken controls)"""
import os, sys, random, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stclient import StServer
from ymmodel import *
R = vcommon.ROOT
D = vcommon.work('sound') + '/'
flaw = sys.argv[1] if len(sys.argv) > 1 else None
recs = load_records(D + 'records.bin')
s = StServer(R)
s('load', snapshot=vcommon.work('fl', 'f1.snap'), disk=vcommon.work('aha.st'))
wid = s('watch_add', lo=0xff8800, hi=0xff8803, kind='w', max_events=1000000)['id']
CH = (0x17b40, 0x17b5a, 0x17b74)

def reset():
    for a in CH:
        s('poke', addr=a, width=4, value=0)
    s('poke', addr=0x17b92, width=1, value=0)
    s('poke', addr=0x17b8e, width=2, value=0)
    s('poke', addr=0x17b90, width=2, value=0)
    s('watch_events', id=wid)

def hw_state():
    ch = [list(struct.unpack('>13h', s.read(a, 26))) for a in CH]
    return ch, s.read(0x17b92, 1)[0], struct.unpack('>h', s.read(0x17b8e, 2))[0]

def tick_hw():
    s('watch_events', id=wid)
    s.call(0x179f6)
    ev = s('watch_events', id=wid)[0]['events']
    out, reg = [], None
    for e in ev:
        v = int(e['value'].lstrip('$'), 16)
        if e['addr'] == '$ff8800': reg = v
        else: out.append((reg, v))
    return out

def norm(st):
    ch, mix, nmax = st
    # a dead channel's words 2..8 are stale and never read before a trigger rewrites them: compare words 0, 1 and the constants
    return ([[x & 0xffff for x in (c if c[0] else c[:2] + [0] * 7 + c[9:])] for c in ch], mix, nmax & 0xffff)

class Count:
    def __init__(self): self.ok = self.n = 0
    def add(self, a, b):
        self.n += 1; self.ok += (a == b)
    def __str__(self): return f'{self.ok}/{self.n}'

# Gate A: each of the 54 ids alone on a cleared engine: post-trigger state, then every tick to silence (cap 400)
trig, writes, states = Count(), Count(), Count()
total_ticks = total_writes = 0
for i in range(54):
    reset()
    m = Sound(recs, flaw)
    s.call(0x17924, d0=i); m.trigger(i)
    trig.add(norm(m.state()), norm(hw_state()))
    for t in range(400):
        hw = tick_hw(); mw = m.tick()
        writes.add(mw, hw); states.add(norm(m.state()), norm(hw_state()))
        total_ticks += 1; total_writes += len(hw)
        if all(c[0] == 0 for c in m.ch) and not hw:
            break
print(f'A single effects: post-trigger state {trig}, per-tick writes {writes}, per-tick state {states}; {total_ticks} ticks, {total_writes} register writes')

# Gate B: random trigger streams (plain and attenuated, three channels, priority and family rules)
rnd = random.Random(12345)
trig, writes, states = Count(), Count(), Count()
nt = nw = 0
for stream in range(40):
    reset()
    m = Sound(recs, flaw)
    for t in range(150):
        k = rnd.random()
        for _ in range(1 + (rnd.random() < 0.3)):
            if rnd.random() < 0.35:
                i = rnd.randrange(1, 54)
                if rnd.random() < 0.5:
                    s.call(0x17924, d0=i); m.trigger(i)
                else:
                    d1 = rnd.randrange(0, 0x3000)
                    s.call(0x1790c, d0=i, d1=d1); m.trigger(i, attenuated=True, d1=d1)
                trig.add(norm(m.state()), norm(hw_state()))
        hw = tick_hw(); mw = m.tick()
        writes.add(mw, hw); states.add(norm(m.state()), norm(hw_state()))
        nt += 1; nw += len(hw)
print(f'B random streams: post-trigger state {trig}, per-tick writes {writes}, per-tick state {states}; {nt} ticks, {nw} register writes')
s.close()
