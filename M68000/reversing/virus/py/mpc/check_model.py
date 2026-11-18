"""Check 3: replay control sequences in the game and compare every tick with exact.py.
    uv run python check_model.py <name>...     (seq_<name>.json -> out_<name>.json; default: every seq_*.json)
Per tick k: exact.step_full(state k, u_k) against the game's state k+1 (pos, vel, att, fuel), the ceiling flag,
exact.ground against D1 after jsr $245b8, and exact.classify against the path markers the game passed."""
import glob, json, os, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import exact, replay as R

names = sys.argv[1:] or sorted(os.path.basename(p)[4:-5] for p in glob.glob(os.path.join(R.WORK, 'seq_*.json')))
objmap0 = None
for name in names:
    ctl = json.load(open(os.path.join(R.WORK, f'seq_{name}.json')))
    out = R.replay(ctl, ground=True)
    json.dump(out, open(os.path.join(R.WORK, f'out_{name}.json'), 'w'))
    T = out['ticks']; N = len(T) - 1 if out['complete'] else len(T) - 1
    dead = None
    if not out['complete']:                 # the last entry is the death tick: no state after it, classify only
        a = T[-1]; m = exact.step_full(a['pos'], a['vel'], a['att'], *a['u'], a['g'], a['fuel'])
        dead = dict(tick=len(T) - 1, path=a['path'], flag_62a62=a['flags']['x_62a62'], hit_62a5d=a['flags']['hit_62a5d'],
                    model_class=exact.classify(m['pos'], exact.snap_objmap), clearance=exact.clearance(m['pos']),
                    vy_after=m['vel'][1], pos_after=m['pos'], vertex_margin_before=min(exact.vertex_margins(a['pos'], a['att'])))
    exact.load(out['snap'])
    n = dict(state=0, fuel=0, ceiling=0, ground=0, cls=0, vtx=0); nhit = 0; minmargin = None; ng = 0; mism = []; paths = {}; ext = []
    for k in range(N):
        a, b = T[k], T[k + 1]
        m = exact.step_full(a['pos'], a['vel'], a['att'], *a['u'], a['g'], a['fuel'])
        for p in a['path']:
            paths.setdefault(p, []).append(k)
        if a['ext']:
            ext.append(k)
        final = (k == N - 1 and not out['complete'])      # the tick that ended the replay: state k+1 is a respawn
        good = (m['pos'] == b['pos'] and m['vel'] == b['vel'] and m['att'] == b['att'])
        n['state'] += good; n['fuel'] += m['fuel'] == b['fuel']
        n['ceiling'] += m['ceiling'] == ('ceiling' in a['path'])
        if a.get('gnd') is not None:
            ng += 1; n['ground'] += exact.ground(m['pos'][0], m['pos'][2]) == a['gnd']
        cls = exact.classify(m['pos'], exact.snap_objmap)
        game = ('ground' if 'ground' in a['path'] else 'object' if 'object' in a['path'] else
                'low' if 'low' in a['path'] else 'free')
        n['cls'] += cls == game
        vh = exact.ship_hits_ground(b['pos'], b['att'])       # the flag the draw between ticks leaves for arrival k+1
        gh = bool(b['flags']['x_62a62'])
        n['vtx'] += vh == gh; nhit += gh
        mg = min(exact.vertex_margins(b['pos'], b['att'])); minmargin = mg if minmargin is None else min(minmargin, mg)
        if vh != gh:
            print('    VERTEX-FLAG MISMATCH tick', k, 'model', vh, 'game', gh, b['pos'], b['att'])
        if not good or cls != game:
            mism.append(dict(tick=k, state_equal=good, model_class=cls, game_path=a['path'], ext=a['ext'],
                             before=dict(pos=a['pos'], vel=a['vel'], att=a['att'], fuel=a['fuel'], u=a['u'],
                                         flags=a['flags']),
                             model=dict(pos=m['pos'], vel=m['vel'], att=m['att'], clearance=exact.clearance(m['pos'])),
                             game=dict(pos=b['pos'], vel=b['vel'], att=b['att']), ends_replay=final))
    ys = [t['pos'][1] for t in T]
    cl = [exact.clearance(t['pos']) for t in T]
    print(f'=== {name}: {len(ctl)} controls, {N} ticks run, complete {out["complete"]}, end {out["end"]}, '
          f'{out["seconds"]} s, {out["steps"]} steps')
    print(f'    state (pos+vel+att) {n["state"]}/{N}; fuel {n["fuel"]}/{N}; ceiling flag {n["ceiling"]}/{N}; '
          f'ground D1 {n["ground"]}/{ng}; path class {n["cls"]}/{N}; '
          f'vertex-contact flag $62a62 at next arrival {n["vtx"]}/{N} (set {nhit}, smallest vertex margin {minmargin})')
    print(f'    y range {min(ys)}..{max(ys)}; clearance range {min(cl)}..{max(cl)}; thrust-on ticks '
          f'{sum(1 for t in T[:N] if t["u"][2] & 2)}; ticks with tilt target outside 0..$7ffe: '
          f'{sum(1 for t in T[:N] if t["u"][0] > 0x7ffe)}')
    print('    paths: ' + ', '.join(f'{p} {len(ks)} (first {ks[0]}, last {ks[-1]})' for p, ks in paths.items())
          + f'; ticks with outside writes to ship/att/fuel: {len(ext)} {ext[:10]}')
    if dead:
        print('    DEATH TICK', json.dumps(dead))
    for mm in mism[:12]:
        print('    MISMATCH', json.dumps(mm))
    if len(mism) > 12:
        print(f'    ... {len(mism) - 12} more mismatches')
