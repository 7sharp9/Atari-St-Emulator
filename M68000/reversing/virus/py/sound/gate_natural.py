"""Gate C: natural play from a snapshot; at every entry of Sound_Tick $179f6 the model is loaded from the live
channel records and must predict that tick's YM writes. Usage: gate_natural.py <snap> <ticks> [flaw]"""
import os, sys, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stclient import StServer
from ymmodel import *
R = vcommon.ROOT
D = vcommon.work('sound') + '/'
snap, nticks = sys.argv[1], int(sys.argv[2])
flaw = sys.argv[3] if len(sys.argv) > 3 else None
recs = load_records(D + 'records.bin')
s = StServer(R)
s('load', snapshot=snap, disk=vcommon.work('aha.st'))
wid = s('watch_add', lo=0xff8800, hi=0xff8803, kind='w', max_events=1000000)['id']
ok = n = nw = 0
fams = {}
active_ticks = 0
for t in range(nticks):
    r = s('run', max_steps=200000, until_pc=0x179f6)
    assert r['reason'] == 'until', r
    ret = struct.unpack('>I', s.read(s.reg('a7'), 4))[0]
    m = Sound(recs, flaw)
    m.ch = [list(struct.unpack('>13h', s.read(a, 26))) for a in (0x17b40, 0x17b5a, 0x17b74)]
    m.mix = s.read(0x17b92, 1)[0]
    for c in m.ch:
        if c[0]: fams[c[1]] = fams.get(c[1], 0) + 1
    active_ticks += any(c[0] for c in m.ch)
    s('watch_events', id=wid)
    r = s('run', max_steps=200000, until_pc=ret)
    assert r['reason'] == 'until', r
    ev = s('watch_events', id=wid)[0]['events']
    hw, reg = [], None
    for e in ev:
        v = int(e['value'].lstrip('$'), 16)
        if e['addr'] == '$ff8800': reg = v
        elif reg is not None and reg <= 13: hw.append((reg, v))
    mw = m.tick()
    n += 1; ok += (mw == hw); nw += len(hw)
    s('step', n=1)
print(f'C natural {snap.split("/")[-1]}: {ok}/{n} ticks predicted exactly ({active_ticks} with a live channel), {nw} YM register 0..13 writes (reg 14 is TOS port A); families seen (ticks): {sorted(fams.items())}')
s.close()
