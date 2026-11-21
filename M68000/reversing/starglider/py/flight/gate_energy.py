"""Gate: the energy / shield rules, read as watch events on the two words (stdrive over g_game1, one fork per leg).

    cd M68000 && ATARI_NOTRACE=1 python3 reversing/starglider/py/flight/gate_energy.py

 energy  606(A6): every main-loop pass the write at $cbee is  new = old - ((speed >> 4) & $1ff)   [legs: speeds 0..479]
 refuel  606(A6): the write at $130ca adds $190 per pass (cap $ffff) while 707(A6) is set at an Energy-Tower gate
 scrape  608(A6): the write at $cc1e is  new = old - $12c  per pass while y >= -20 (ground) with speed > 0
 death   300(A6) = 1 when energy would underflow (energy := 0); 300(A6) = 2 when the shield would (shield := 0)
Prints one `leg: MATCH k/n` line per rule."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flightlib import *

dr = new_drive(sg.work('flight', 'j_energy.jsonl'))
f0 = dr.fork()

def events(wid):
    return dr.rpc('watch_events', id=wid)[0]['events']

def watch(off):
    return dr.rpc('watch_add', lo=G + off, hi=G + off + 1, kind='w', max_events=5000)['id']

def pcof(e): return int(e['pc'].lstrip('$'), 16)
def val(e): return int(e['value'].lstrip('$'), 16)

# ---- energy drain per pass vs speed
ok = n = 0
for spd in (0, 15, 16, 20, 100, 300, 479):
    dr.restore(f0)
    w = watch(606)
    dr.poke(G + 606, 2, 40000); dr.poke(0xc3d4, 2, -spd & 0xffff)
    dr.step(500000)
    ev = [e for e in events(w) if pcof(e) == 0xcbee]
    vs = [val(e) for e in ev]               # the first pass may still use the old speed word: skipped below
    for a, b in zip(vs[1:], vs[2:]):
        n += 1; ok += (a - b == (spd >> 4) & 0x1ff)
    dr.rpc('watch_remove', id=w)
print(f'energy drain: MATCH {ok}/{n}  (speeds 0,15,16,20,100,300,479; 7 legs x ~10 passes)')

# ---- refuel at the tower gate (g_game1 object #14 at (7872,*,9872), type 11)
ok = n = 0
for (heading, expect, start) in ((0x800, True, 60000), (0x000, False, 60000), (0x800, True, 65400)):
    dr.restore(f0)
    w = watch(606)
    dr.poke(G + 302, 2, 7872); dr.poke(G + 306, 2, 11852); dr.poke(G + 316, 2, heading)
    dr.poke(0xc3d4, 2, 0); dr.poke(G + 606, 2, start)
    dr.step(500000)
    ev = events(w)
    adds = [e for e in ev if pcof(e) == 0x130ca]
    vs = [val(e) for e in ev]
    flag = dr.u8(G + 707)
    if expect:
        for a, b in zip(vs, vs[1:]):
            if b != a:
                n += 1; ok += (b - a == 0x190 or b == 0xffff)
        print(f'  gate heading ${heading:x}, start {start}: 707={flag:#x}, {len(adds)} refuel writes, energy {vs[0]} -> {vs[-1]}')
        if start > 65000: n += 1; ok += (vs[-1] == 0xffff)
    else:
        n += 1; ok += (len(adds) == 0 and flag == 0)
        print(f'  control heading ${heading:x}: 707={flag:#x}, {len(adds)} refuel writes')
    dr.rpc('watch_remove', id=w)
print(f'refuel: MATCH {ok}/{n}')

# ---- ground scrape: shield -= $12c per pass at y >= -20 (stick forward so the craft stays down)
ok = n = 0
dr.restore(f0)
w = watch(608)
dr.poke(G + 304, 2, -10); dr.poke(0xc3d0, 2, -250 & 0xffff); dr.poke(0xc3d4, 2, -100 & 0xffff); dr.poke(G + 608, 2, 60000)
dr.step(300000)
ev = events(w)
vs = [val(e) for e in ev]
scr = [e for e in ev if pcof(e) == 0xcc1e]
for a, b in zip(vs, vs[1:]):
    n += 1; ok += (a - b == 0x12c)
print(f'ground scrape: MATCH {ok}/{n}  ({len(scr)} writes at $cc1e, y now {dr.s16(G+304)})')
dr.rpc('watch_remove', id=w)

# ---- death: energy underflow -> 300=1; shield underflow -> 300=2
res = {}
for name, off, setup in (('energy', 606, {}), ('shield', 608, {})):
    dr.restore(f0)
    if name == 'energy':
        dr.poke(G + 606, 2, 3); dr.poke(0xc3d4, 2, -479 & 0xffff)
    else:
        dr.poke(G + 304, 2, -10); dr.poke(0xc3d0, 2, -250 & 0xffff); dr.poke(0xc3d4, 2, -100 & 0xffff); dr.poke(G + 608, 2, 200)
    dr.step(200000)
    res[name] = (dr.u16(G + 300), dr.u16(G + off))
print(f'death: energy leg 300={res["energy"][0]} energy={res["energy"][1]}; shield leg 300={res["shield"][0]} shield={res["shield"][1]}'
      f'  ({"MATCH 2/2" if res["energy"] == (1, 0) and res["shield"] == (2, 0) else "MISMATCH"})')
dr.close()
