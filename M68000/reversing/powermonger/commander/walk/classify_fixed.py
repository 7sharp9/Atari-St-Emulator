"""classify_fixed.py - the census's class b/c pairs (bc_full.json from list206.py + model206.py) under the fixed walker:
walker.simulate from the man's full record state (mode, dwell, heading, sweep, step), chase (prev $2e) against the
chased entity standing at the target words, a follower's $4a target = the lead's position in the snapshot, and the
$14fa2 hand-off reading the group state from the snapshot. Redispatch resets come from the game traces
(census_cmp.json) where they exist.
Usage: classify_fixed.py bc_full.json"""
import json, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
import os as _os
WORK = next(p for p in HERE.parents if (p / 'tools' / 'rdis.py').exists()) / _os.environ.get('CMD_WORK', 'scratchpad/cmd1') / 'walk'
WORK.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE))
import walker
d = json.load(open(sys.argv[1]))
cmp = {(r['snap'], r['obj']): r for f in ('census_cmp.json', 'census_cmp_flip.json') if (WORK / f).exists() for r in json.load(open(WORK / f))}
T = Counter()
# a 1000M-step watch run (long50.txt / long50.cmp: 3870/3870 own ticks match, on his target before step +369M)
LONG = {('X10G_k143_c12', 50): 'arrives'}
mp = None
rows = []
for x in d:
    if mp is None or mp.snap != x['snap']:
        mp = walker.astar.Map(x['snap'])
        mp.snap = x['snap']
    r = mp.ram
    st = walker.decode(bytes.fromhex(x['rec']))
    lead = None
    if st['w28']:
        o = 0x51b66 + st['w28']
        lead = (int.from_bytes(r[o + 8:o + 10], 'big', signed=True), int.from_bytes(r[o + 10:o + 12], 'big', signed=True))
    gs = lambda off: int.from_bytes(r[0x51538 + off:0x51538 + off + 2], 'big')
    try:
        arr, tick, _s = walker.simulate(mp, st, 3000, group_state=gs, lead_pos=lead, chase_static=True)
        fixed = 'arrives' if arr else 'stuck'
    except walker.Unmodelled as e:
        fixed = 'unmodelled ' + str(e)
    old = 'arrives' if x['arrives'] else 'stuck'
    c = cmp.get((Path(x['snap']).stem, x['obj']))
    game = None
    if c is not None:
        game = 'arrives' if c['arrived'] is not None else 'stuck'
        replay = 'arrives' if c['rep_arr'] is not None else 'stuck'
    if (Path(x['snap']).stem, x['obj']) in LONG:
        game = LONG[(Path(x['snap']).stem, x['obj'])]
    census = 'arrives' if x['cls'] == 'c' else 'stuck'      # classify_stuck's reading of the game
    truth = game or census
    final = replay if (c is not None and c['verdict'].startswith('plain arrives, game redis')) else fixed
    T[(x['cls'], 'old ' + old, 'fixed ' + final, 'game ' + truth)] += 1
    rows.append(dict(snap=Path(x['snap']).stem, obj=x['obj'], cls=x['cls'], old=old, fixed=fixed, final=final, truth=truth,
                     traced=c is not None))
for k, v in sorted(T.items()):
    print(v, k)
dis_old = sum(1 for z in rows if z['cls'] == 'b' and z['old'] != z['truth'])
dis_new = sum(1 for z in rows if z['cls'] == 'b' and z['final'] != z['truth'])
print('class b disagreements: old model %d, fixed model %d' % (dis_old, dis_new))
print('class c disagreements: old %d, fixed %d' % (sum(1 for z in rows if z['cls'] == 'c' and z['old'] != z['truth']),
                                                    sum(1 for z in rows if z['cls'] == 'c' and z['final'] != z['truth'])))
json.dump(rows, open(WORK / 'classify_fixed.json', 'w'))
