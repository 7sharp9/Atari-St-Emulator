"""Gates for shot.py against shot_capture.py runs: spawn, flight, hit, terrain, kill.

    uv run python gate_shot.py cap_auto.json [cap_autofire.json ...] [--control none|shift|noskip|grav|box80|boxc0|order|life|terr]

Controls break the model on purpose (each must lower a count):
  shift  jitter shift 13 instead of 14          noskip  no RNG skip for the thrust exhaust
  grav   gravity added before the move          life    life tested after the decrement as <= 0
  box80 / boxc0  hit box half-width $80 / $c0   order   actors tested last-to-first
  terr   object band $170 -> $70             gnd     the actors' cell height map as the shot's ground
"""
import json, struct, sys
import shot as S

args = sys.argv[1:]
control = 'none'
if '--control' in args:
    i = args.index('--control'); control = args[i + 1]; del args[i:i + 2]

if control == 'shift':
    _j = S.jitter3
    S.jitter3 = lambda st, shift=14: _j(st, 13)
if control == 'noskip':
    S.EXHAUST_DRAWS = 0
if control == 'grav':
    def fly(rec, g):
        x, y, z, vx, vy, vz, life = rec
        life -= 1
        if life < 0: return None
        vy = S.s16(vy + g)
        return [S.s16(x + vx), S.s16(y + vy), S.s16(z + vz), vx, vy, vz, life]
    S.fly = fly
if control == 'life':
    _f = S.fly
    S.fly = lambda rec, g: None if rec[6] - 1 <= 0 else _f(rec, g)
if control == 'box80': S.BOX = 0x80
if control == 'boxc0': S.BOX = 0xc0
if control == 'order':
    _h = S.hits
    def hits(rec, actors):
        i = _h(rec, actors[::-1])
        return None if i is None else len(actors) - 1 - i
    S.hits = hits
if control == 'terr':            # object band $170 -> $70 above the ground
    _t = S.terrain
    def terrain(rec, objmap=None):
        h, t = S.ground_type(rec[0], rec[2])
        return 'fly' if 0x70 <= S.s16(h - rec[1]) < 0x170 else _t(rec, objmap)
    S.terrain = terrain
if control == 'gnd':             # the actors' cell height map instead of the sum of sines
    S.exact.ground = S.aground

T = {k: [0, 0] for k in ('spawn_rec', 'spawn_rng', 'tick_rng_align', 'tick_spawn', 'tick_fuel', 'tick_score',
                         'nofire', 'flight', 'expire', 'hit', 'nohit', 'terrain_removed', 'terrain_fly',
                         'next_multiset', 'kill_event', 'kill')}
real_hits = 0; kinds = {}; margins = {'in': [], 'out': []}; mapdiff = 0; reasons = {}
kill_rows = []; kev_rows = []; edge = []


def tally(name, ok):
    T[name][0] += bool(ok); T[name][1] += 1


def rec7(h):
    return list(struct.unpack('>7h', bytes.fromhex(h)[:14]))


for path in args:
    D = json.load(open(path)); rows = D['rows']
    omap = bytearray.fromhex(D['map0'])
    for k in range(len(rows) - 1):
        r = rows[k]; nx = rows[k + 1]
        ev = r['ev']
        # ---- spawn
        used = r['u'] if r['u'] is not None else r['d']
        st = dict(pos=r['pos'], vel=r['vel'], att=r['att'], g=r['g'], fuel=r['fuel'], latch=r['flags']['latch_62a63'])
        rng0 = S.rng_from_hex(r['rng'])
        pre = [e for e in ev if e['e'] == 'fire_pre']; post = [e for e in ev if e['e'] == 'fire_post']
        dead = any(e['e'] in ('dead', 'crash') for e in ev)
        new = None
        if dead:
            pass
        else:
            prec, prng, pfuel, pds = S.spawn_from_tick(st, used, rng0, r['nobj'])
            if pre:
                e = pre[0]; q = post[0]
                # low level: from the registers' inputs (position at arrival, D3..D5, the matrix at the fire code)
                lrec, lrng = S.spawn(r['pos'], [S.s16(v) for v in e['d345']], bytes.fromhex(e['matrix']),
                                     S.rng_from_hex(e['rng']))
                got = rec7(q['rec'])
                tally('spawn_rec', lrec == got and int(q['rec'][28:], 16) == S.HANDLER)
                tally('spawn_rng', lrng == S.rng_from_hex(q['rng']))
                # from the arrival state
                tally('tick_spawn', prec == got)
                tally('tick_rng_align', prng == S.rng_from_hex(q['rng']))
                new = got
            else:
                tally('nofire', prec is None)
            tally('tick_fuel', pfuel == nx['fuel'] or any(e['e'] == 'pad' for e in ev))
            aw = sum(e['award'] for e in ev if e['e'] == 'kill') + 40 * sum(e['e'] == 'award40' for e in ev) \
                + 1000 * sum(e['e'] == 'award1000' for e in ev)
            tally('tick_score', nx['score'] - r['score'] == pds + aw)
        # ---- flight / hit / terrain
        shots = [o[:7] for o in S.unpack_obj(r['obj']) if o[7] == S.HANDLER]
        if new is not None:
            shots.append(new)
        actors = S.unpack_pool(nx['pool'])
        omap_after = bytearray(omap)
        for a, w, v in r['mapw']:
            for i in range(w):
                omap_after[a - 0x32a58 + i] = (v >> (8 * (w - 1 - i))) & 0xff
        hit_ev = [(rec7(e['shot']), e['idx']) for e in ev if e['e'] == 'hit']
        rem_ev = []; pend = []
        for e in ev:
            if e['e'] in ('below', 'boom', 'water', 'obj_fresh', 'hit'):
                pend.append(e['e'])
            elif e['e'] == 'h_remove':
                # the shot's own events are the suffix from its 'below' or 'obj_fresh' (a 'water' or 'boom' left by
                # another handler's removal, which shot_capture.py drops, can precede it)
                if 'below' in pend: pend = pend[len(pend) - 1 - pend[::-1].index('below'):]
                elif 'obj_fresh' in pend: pend = pend[len(pend) - 1 - pend[::-1].index('obj_fresh'):]
                else: pend = pend[-1:]
                rem_ev.append((rec7(e['rec']), tuple(pend))); pend = []
            elif e['e'] in ('fire_pre', 'fire_post', 'kill'):
                pend = []
        nshots = sorted(tuple(o[:7]) for o in S.unpack_obj(nx['obj']) if o[7] == S.HANDLER)
        survivors = []
        if not dead:
            for s in shots:
                r2, what, idx = S.step(s, r['g'], actors, omap)
                r2b, whatb, idxb = S.step(s, r['g'], actors, omap_after)
                if what != whatb: mapdiff += 1
                f = S.fly(s, r['g'])
                if what == 'expired':
                    tally('expire', True)       # checked by the multiset below
                    continue
                # nearest-miss / deepest-hit margins of the box, per actor
                for a in actors:
                    dd = [a[0] - f[0], a[2] - f[2], a[1] - f[1]]
                    inside = all(S.in_box(d, 0xa0) for d in dd)
                    m = max(max(S.s16(d) - 0x9f, -0xa0 - S.s16(d)) for d in dd)   # <= 0 inside
                    margins['in' if inside else 'out'].append(m)
                    if inside and m >= -8: edge.append([S.s16(d) for d in dd])
                if what == 'hit':
                    ok = (f, idx) in hit_ev
                    tally('hit', ok)
                    if not ok: print(path, k, 'predicted hit not seen', f, idx, hit_ev)
                else:
                    ok = not any(h[0] == f for h in hit_ev)
                    tally('nohit', ok)
                    if what == 'fly':
                        tally('terrain_fly', not any(x[0] == f for x in rem_ev))
                        survivors.append(tuple(f))
                    else:
                        want = {'ground': ('below', 'boom'), 'water': ('below', 'water'), 'object': ('obj_fresh',),
                                'wreck': ('boom',)}[what]
                        okk = (f, want) in rem_ev
                        tally('terrain_removed', okk)
                        reasons[what] = reasons.get(what, 0) + 1
                        if not okk and control == 'none':
                            print(path, k, 'terrain', what, f, [x for x in rem_ev if x[0] == f])
            for sh, idx in hit_ev:
                real_hits += 1
                b = actors[idx][8]; kinds[S.KINDS[b][:2]] = kinds.get(S.KINDS[b][:2], 0) + 1
                if not any(S.fly(s, r['g']) == sh and S.step(s, r['g'], actors, omap)[1:] == ('hit', idx) for s in shots):
                    tally('hit', False); print(path, k, 'real hit not predicted', sh, idx)
            tally('next_multiset', sorted(survivors) == nshots)
            tally('flight', all(s in nshots for s in survivors))
        omap = omap_after
        # ---- kill: a hit in interval k -> award and removal in tick k+1's actor walker
        for sh, idx in dict(((tuple(a), b), 0) for a, b in hit_ev):
            b = actors[idx][8]; kind, state, award, can = S.KINDS[b]
            kev = [e for e in nx['ev'] if e['e'] == 'kill' and e['idx'] == idx]
            tally('kill_event', can and len(kev) == 1 and kev[0]['award'] == award and bool(actors[idx][6] & 0x8000))
            kev_rows.append((path, k, kind, state, award, [e['award'] for e in kev]))
            if k + 2 >= len(rows):
                continue
            fired = any(e['e'] == 'fire_pre' for e in nx['ev'])
            other = sum(e['award'] for e in nx['ev'] if e['e'] == 'kill' and e['idx'] != idx)
            a40 = 40 * sum(1 for e in nx['ev'] if e['e'] == 'award40')
            dscore = rows[k + 2]['score'] - nx['score']
            ok = (can and len(kev) == 1 and kev[0]['award'] == award and dscore == award - fired + other + a40
                  and rows[k + 2]['npool'] == nx['npool'] - 1 - (1 if other else 0)
                  and bool(actors[idx][6] & 0x8000))
            tally('kill', ok)
            kill_rows.append((path, k, kind, state, award, dscore, fired, ok))

print('control:', control)
for k, (a, b) in T.items():
    print(f'  {k:16s} {a}/{b}')
print('real hits (hit events):', real_hits, 'by target state:', kinds)
print('terrain removals predicted by kind:', reasons, '; outcomes that differ between the map before and after the tick\'s writes:', mapdiff)
if margins['in']:
    print('box margins over all (shot, actor) pairs: inside', len(margins['in']), 'closest to the edge', max(margins['in']),
          '; outside', len(margins['out']), 'nearest miss', min(margins['out']))
print('hits within 8 of a box face (actor - shot on x, z, y):', edge)
for row in kev_rows:
    print('  kill_event', row)
for row in kill_rows:
    print('  kill', row)
