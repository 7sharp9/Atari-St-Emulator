"""Differential test of the whole $df18 frame (port: ssport.frame) against callcap over live natural-play frames.
usage: test_df18.py [nframes] [seed]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from difflib_ss import *
if os.environ.get('SS_MUTATE') == 'floor':      # negative control: floor division instead of DIVS truncation must be caught
    P.divs = lambda a, b: a // b

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
h = Harness(sscfg.SNAP_RACE)
drv = Driver(h, seed)
ok = 0
bad_states = []
fieldbad = {}
cover = {}
NAMES = {P.FLAG:'FLAG', P.STUN:'STUN', P.BUMP:'BUMP', P.F1:'F1', P.F2:'F2', P.GATE:'GATE', P.SECTOR:'SECTOR', P.LAPS:'LAPS', P.SAFEX:'SAFE', P.SPD:'SPD', P.TGT:'TGT', P.TURN:'TURN', P.VX:'VX', P.WRENCH:'WRENCH'}
for i in range(N):
    drv.poke_input()
    regs = h.run_to(0xdf18, 1)
    if regs is None:
        print('bpc miss'); break
    ram = h.snap_ram()
    mapbase = ram.gl(-1910)
    mem, d, outc = h.callcap(0xdf18)
    m = P.Mem(ram.b)
    P.frame(m)
    bad = compare(ram.b, m, d, mapbase)
    ed = emu_delta(d, mapbase)
    touched = set()
    for a in ed:
        if ed[a] != ram.b[a]:
            off = a - A4
            for base, nm in NAMES.items():
                if base <= off < base + 8:
                    touched.add(nm)
            if -1910 <= off < 0 and False: pass
            if mapbase <= a < mapbase + 1000: touched.add('MAPCELL')
            if off in (-4086, -4085): touched.add('-4086')
    for t in touched: cover[t] = cover.get(t, 0) + 1
    if not bad:
        ok += 1
    else:
        bad_states.append((i, bad))
        for a, pv, ev in bad:
            fieldbad[field_name(a)] = fieldbad.get(field_name(a), 0) + 1
print('frames in which the emulator changed field:', cover)
print('df18 frames matching: %d/%d' % (ok, N))
print('mismatching fields:', dict(sorted(fieldbad.items(), key=lambda kv: -kv[1])[:30]))
for i, bad in bad_states[:5]:
    print('state', i, [(field_name(a), pv, ev) for a, pv, ev in bad[:12]])
h.close()
