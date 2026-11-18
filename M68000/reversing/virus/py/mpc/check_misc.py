"""Small checks.   uv run python check_misc.py
 a) empty fuel (POKED: fuel word $32a2e := 7 at arrival 0, then 6 thrust ticks, the last two also firing): exact.step_full
    against the game.
 b) positive control for the outside-writer watches: the same watch ranges with the PC filter turned to the tick routine
    itself must report writes every tick.
 c) the inputs the mouse routine produced in cap/flight_bp.txt, and the range of its magnitude table $d9fa.
 d) totals over out_*.json (run check_model.py first)."""
import glob, json, os, re, struct, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import exact, replay as R

g = R.Game()
g.run_to_tick(400000)
g.s('poke', addr=0x32a2e, width=2, value=7)
ctl = [[0x1000, 0xc000, 2]] * 4 + [[0x1000, 0xc000, 3]] * 2
T = []
for u in ctl:
    regs, st = g.state(); g.set_controls(regs, u); st['u'] = u
    ok, path, *_ = g.run_to_tick(400000); st['path'] = path; T.append(st)
T.append(g.state()[1])
okc = 0
for a, b in zip(T, T[1:]):
    m = exact.step_full(a['pos'], a['vel'], a['att'], *a['u'], a['g'], a['fuel'])
    good = (m['pos'], m['vel'], m['att'], m['fuel']) == (b['pos'], b['vel'], b['att'], b['fuel'])
    okc += good
    print('  fuel', a['fuel'], '->', b['fuel'], 'model', m['fuel'], 'path', a['path'], 'thrust applied (model)', m['thrust'], 'equal', good)
print(f'a) empty fuel, poked: {okc}/{len(ctl)} ticks equal (pos, vel, att, fuel)')

# b) watch positive control
ids = []
for lo, hi in ((0x270b0, 0x270bb), (0x32a32, 0x32a35), (0x32a2e, 0x32a2f)):
    ids.append(g.s('watch_add', lo=lo, hi=hi, kind='w', pc_lo=R.TICK_LO, pc_hi=R.TICK_HI, source='cpu')['id'])
tot = 0; outside = 0
for k in range(5):
    regs, st = g.state(); g.set_controls(regs, [0x1000, 0xc000, 0])
    left = 400000
    while True:
        r = g.s('run', max_steps=left)
        for wid, n in (r.get('watch_hits') or {}).items():
            if int(wid) in ids: tot += n
            else: outside += n
        if R.hx(r['pc']) == R.TICK: break
print(f'b) watch control: {tot} writes to ship/att/fuel from PCs inside the tick routine over 5 ticks (raw last run: {r}); '
      f'{outside} from outside')
g.close()

# c) mouse routine outputs in the capture
txt = open(os.path.join(R.ROOT, 'scratchpad', 'virus', 'cap', 'flight_bp.txt')).read()
ds = re.findall(r'D0:([0-9a-f]{8}) D1:([0-9a-f]{8}) D2:([0-9a-f]{8})', txt)
vals = {}
for d in ds: vals[d] = vals.get(d, 0) + 1
print('c) distinct (D0, D1, D2) register lines in the capture (each stop prints r twice):', vals)
exact.load(); ram = exact._RAM
t9 = struct.unpack('>128H', ram[0xd9fa:0xd9fa + 256]); t8 = struct.unpack('>128H', ram[0xd8fa:0xd8fa + 256])
print(f'   magnitude table $d9fa (128 words): min ${min(t9):x} max ${max(t9):x} first {[hex(v) for v in t9[:4]]} last {[hex(v) for v in t9[-3:]]}')
print(f'   angle table $d8fa (128 words): min ${min(t8):x} max ${max(t8):x}')

# d) totals
tot = dict(ticks=0, state=0, deaths={}, low=0, ext=0, ceiling=0)
for p in sorted(glob.glob(os.path.join(R.WORK, 'out_*.json'))):
    o = json.load(open(p)); T = o['ticks']
    N = len(T) - 1
    for k in range(N):
        a, b = T[k], T[k + 1]
        m = exact.step_full(a['pos'], a['vel'], a['att'], *a['u'], a['g'], a['fuel'])
        if 'pad' in a['path'] or 'landed' in a['path']:
            continue
        tot['ticks'] += 1; tot['state'] += (m['pos'], m['vel'], m['att'], m['fuel']) == (b['pos'], b['vel'], b['att'], b['fuel'])
        tot['low'] += 'low' in a['path']; tot['ceiling'] += 'ceiling' in a['path']; tot['ext'] += bool(a['ext'])
    if not o['complete']:
        key = ','.join(T[-1]['path']); tot['deaths'][key] = tot['deaths'].get(key, 0) + 1
print('d) totals over', len(glob.glob(os.path.join(R.WORK, 'out_*.json'))), 'out files (pad and landing ticks excluded):', tot)
