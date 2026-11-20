"""Aggregate work/gNNN.json (death_census.py) into the cause x wave table and per-death rows.   uv run python aggregate.py [dir of gNNN.json; default $VIRUS_WORK/deaths/saved]"""
import json, glob, os, sys, collections
here = os.path.dirname(os.path.abspath(__file__))
ROOT = here
while not os.path.exists(os.path.join(ROOT, 'tools', 'rdis.py')): ROOT = os.path.dirname(ROOT)
W = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('VIRUS_WORK', os.path.join(ROOT, 'scratchpad', 'virus')), 'deaths', 'saved')
rows = []
for f in sorted(glob.glob(os.path.join(W, 'g[0-9][0-9][0-9].json'))):
    r = json.load(open(f))
    for i, d in enumerate(r['deaths']):
        s = d['state']
        if s is None: continue
        cause = d['cause']
        if cause == 'flag:NO_SETTER_STOP' and d['entry'] == '25ad8' and s['flag5d'] == 0: cause = 'object_cell:2004a'
        if cause.startswith('object_cell'):
            cat = 'object cell (bit 5, $2004a), ' + ('fuel 0' if s['fuel'] == 0 else 'fuel > 0')
        elif cause.startswith('ground'):
            cat = 'ground, fuel 0' if s['fuel'] == 0 else 'ground, fuel > 0'
        else:
            cat = cause.split(':')[1] + (', fuel 0' if s['fuel'] == 0 else ', fuel > 0')
        rows.append(dict(game=r['game'], n=i + 1, wave=s['wave'], tick=s['tick'], fuel=s['fuel'], cat=cat, cause=cause,
                         life_ticks=None, a500=d['a500'], hits500=d['hits500'], near=s['nearest_actor'][0] if s['nearest_actor'] else None,
                         replay_end=d['approach']['replay_end'] if 'approach' in d else None, d=d))
if __name__ == '__main__':
    print(len(rows), 'life losses over', len({r['game'] for r in rows}), 'games')
    cats = sorted({r['cat'] for r in rows}); waves = sorted({r['wave'] for r in rows})
    print('%-28s' % 'cause \\ wave idx', *['%5d' % w for w in waves], '  total')
    for c in cats:
        print('%-28s' % c, *['%5d' % sum(1 for r in rows if r['cat'] == c and r['wave'] == w) for w in waves], '%7d' % sum(1 for r in rows if r['cat'] == c))
    print('%-28s' % 'total', *['%5d' % sum(1 for r in rows if r['wave'] == w) for w in waves], '%7d' % len(rows))
    print('\nfuel at death: fuel==0', sum(1 for r in rows if r['fuel'] == 0), 'of', len(rows))
    print('\nnearest actor kind by cause (distance bound shown as median)')
    by = collections.defaultdict(list)
    for r in rows:
        if r['near']: by[r['cat'].split(',')[0]].append(r['near'])
    for c, v in sorted(by.items()):
        cnt = collections.Counter(x[1] for x in v); ds = sorted(x[0] for x in v)
        print(f'  {c:36s} n={len(v):3d} median dist {ds[len(ds)//2]:6d}  ', dict(cnt.most_common(4)))
    print('\nfuel supply and drain per life (classes from a_life, summed over deaths with a_life from the new code)')
    tot = collections.Counter(); n = 0
    for r in rows:
        a = r['d'].get('a_life')
        if a and 'life_start' in str(a) or (a and ('wave_start' in a or 'pad_refuel' in a)):
            pass
    for r in rows:
        a = r['d'].get('a_life') or {}
        if r['d'].get('life_start_step') is None: continue
        n += 1
        for k, v in a.items(): tot[k] += v
    print('  ', n, 'lives', dict(tot))
    print('\nper death')
    for r in rows:
        a = r['a500']; n = r['near']
        print(f"g{r['game']:03d}#{r['n']} w{r['wave']} t{r['tick']} {r['cause']:34s} fuel {r['fuel']:5d} 500t: " + ' '.join(f'{k}{v:+d}' for k, v in sorted(a.items())) + f"  near {n[1] if n else None}@{n[0] if n else None}")
