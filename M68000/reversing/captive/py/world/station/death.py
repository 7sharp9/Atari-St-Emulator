#!/usr/bin/env python3
"""Why does the final base (station landing, 14794 = 10) end in "DROID'S HAVE FAILED"? Replays station.py's arm 10
(labelled poke 14794 = 10), then logs the base state in 250k-step chunks and watches 14800, 410 and 13410.
  uv run python -I reversing/captive/py/world/station/death.py [natural]      'natural' = control: base1/site.snap target-1 landing instead
Outputs: death_*.png under scratchpad/captive/station/; stdout is the log (redirect it).
  'trace' as an extra argument: first reach of each hit/death routine and the group list (about 100 s)."""
import os, sys, struct
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    nd = os.path.dirname(d)
    if nd == d: sys.exit('repo root not found')
    d = nd
R = os.environ.get('M68000_ROOT') or d
sys.path.insert(0, os.path.join(R, 'tools'))
from stclient import StServer
A6 = 0x1b5ce
W = os.path.join(R, 'scratchpad', 'captive')
OUT = os.path.join(W, 'station')
w16 = lambda s, o: struct.unpack('>h', s.read(A6 + o, 2))[0]
l32 = lambda s, o: struct.unpack('>I', s.read(A6 + o, 4))[0]
nat = len(sys.argv) > 1 and sys.argv[1] == 'natural'
tag = 'nat' if nat else 'fin'
s = StServer(R)
def pin():
    for _ in range(3):
        s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
def goto(px, py):
    pin(); x = y = 0
    while (x, y) != (px, py):
        dx, dy = min(127, px - x), min(127, py - y)
        s('mouse', action='move', dx=dx, dy=dy); s('step', n=30000); x += dx; y += dy
def click(px, py, settle):
    goto(px, py); s('mouse', action='down', button='l'); s('step', n=60000)
    s('mouse', action='up', button='l'); s('step', n=settle)
def party(): p = l32(s, 26); return (p >> 16, p & 0xffff)
def st(): return dict(mode=w16(s, 13564), s13410=w16(s, 13410), live410=w16(s, 410), e14800=w16(s, 14800), party=party(), face=w16(s, 30), mission=w16(s, 14776), cnt=w16(s, 14794))

if nat:
    s('load', snapshot=os.path.join(W, 'base1', 'site.snap'))
    click_orbit = lambda: (s('mouse', action='move', dx=100, dy=-34), s('step', n=30000), s('mouse', action='down', button='l'), s('step', n=60000), s('mouse', action='up', button='l'), s('step', n=30_000_000))
    click_orbit()
    s('mouse', action='move', dx=49, dy=-2); s('step', n=30000)
else:
    s('load', snapshot=os.path.join(W, 'mission1.snap'), disk=os.path.join(W, 'tmb097.st'))
    click(78, 85, 300000)
    s('poke', addr=A6 + 14794, width=2, value=10)        # LABELLED POKE (as station.py arm 10)
    click(204, 76, 0)
    for _ in range(200):
        s('step', n=500000)
        if w16(s, 14858) == 6: break
    goto(252, 75)
print(tag, 'before LAND', st(), 'ship', w16(s, 14858))
for a in (14800, 410, 13410):
    s('watch_add', lo=A6 + a, hi=A6 + a + 1, kind='w')
HITS = ['$b5c2', '$b5c6', '$876a', '$8758', '$86e0', '$f884', '$fac4', '$fad6', '$e6dc', '$9a9a', '$107cc', '$bf38', '$87d6', '$134b8']
s('mouse', action='down', button='l'); s('step', n=60000); s('mouse', action='up', button='l')
r = s('run', max_steps=25_000_000, until_pc=[0xb5c2, 0xb5c2 | 0x80000000])
print('to $b5c2:', r['reason'], 'D0', hex(s.reg('d0') & 0xffff), 'D2', s.reg('d2') & 0xffff, 'step', r.get('steps', ''), st())
r = s('run', max_steps=3_000_000, until_pc=[0xb5c6, 0xb5c6 | 0x80000000])
print('to $b5c6 (generator returned):', r['reason'], st())
base = s('fork')['id']
if 'trace' in sys.argv:
    # per-PC census of the first 12M steps (positive control: $b5c6 already passed), then each routine's first reach
    pcs = ['$985a', '$10732', '$1073c', '$10e4a', '$f4b0', '$10eec', '$f884', '$9a9a', '$e6dc', '$876a']
    # stop at the first reach of each, in order of occurrence, printing step offset, stack top and the group record near A0-A5
    seen = {}
    for _ in range(60):
        r = s('run', max_steps=2_000_000, until_pc=[int(x[1:], 16) for x in pcs] + [int(x[1:], 16) | 0x80000000 for x in pcs])
        if r['reason'] != 'until': 
            continue
        pc = s.reg('pc') & 0xffffff
        if pc in seen and pc not in (0xf884,):
            s('step', n=1); continue
        seen[pc] = seen.get(pc, 0) + 1
        if seen[pc] > 2: s('step', n=1); continue
        sp = s.reg('a7'); stk = struct.unpack('>6I', s.read(sp, 24))
        gr = []
        for i in range(6):
            av = s.reg(f'a{i}') & 0xffffff
            if 0x1c782 <= av < 0x1d152:
                gr.append((f'a{i}', hex(av), s.read(av, 16).hex()))
        print(f'${pc:x} #{seen[pc]} party {party()} stack', ' '.join(f'{x:x}' for x in stk), 'groups', gr, 'live410', w16(s, 410))
        s('step', n=1)
        if pc == 0x10e4a:
            a0 = s.reg('a0') & 0xffffff; print('   $10e4a A0 =', hex(a0), s.read(a0, 16).hex(), 'A1-A5', [hex(s.reg(f'a{i}') & 0xffffff) for i in range(1, 6)])
        if pc == 0x876a: break
    g = A6 + 4532; n = 0
    print('group list from 4532(A6) =', hex(g), '; party', party(), '; groups within 8 cells (addr x y size flags type hp):')
    while True:
        rec = s.read(g, 16); size = struct.unpack('>h', rec[2:4])[0]
        if size <= 0 or n > 400: break
        x, y = rec[0], rec[1]
        if abs(x - party()[0]) <= 8 and abs(y - party()[1]) <= 8 or rec[8] == 0x1f or g <= 0x1d342 < g + size or g <= 0x1d222 < g + size:
            print(f'   {g:x} ({x},{y}) size {size} flags4={rec[4]:02x} +5={rec[5]:02x} timer/period {rec[6]}/{rec[7]} type {rec[8]:02x} hp {struct.unpack(">h", rec[10:12])[0]}')
        g += size; n += 1
    print('   groups total', n)
    s('render', path=os.path.join(OUT, 'death_fin_trace_end.png'))
    s.close(); sys.exit()
# census over 40M steps after generation, in chunks, logging the state
total = 0; chunk = 1_000_000; agg = {}
os.makedirs(OUT, exist_ok=True)
rendered = set()
while total < 40_000_000:
    h = s('hits', steps=chunk, addrs=HITS)
    total += chunk
    for x in h['hits']:
        if x['count']: agg.setdefault(x['addr'], []).append((total, x['count']))
    if total in (500_000 * 0 + 1_000_000, 4_000_000) or total % 10_000_000 == 0:
        print(f'+{total}: {st()}')
        s('render', path=os.path.join(OUT, f'death_{tag}_{total // 1_000_000}M.png'))
    if w16(s, 14800) != 0 and not nat:
        print(f'14800 = {w16(s,14800)} by +{total}'); break
print('hits (chunk end step after $b5c6, count):', agg)
for w in s('watch_events'):
    print('watch', w['id'], [(e['step'], e['pc'], e['addr'], e['value']) for e in w['events']][:40])
s.close()
