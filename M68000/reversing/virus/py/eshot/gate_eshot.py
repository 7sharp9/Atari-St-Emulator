"""Gate for the enemy shot model (eshot.py) against natural captures (cap_eshot.py).

    uv run python gate_eshot.py <cap.json> [...] [--control name]

spawn:   per $22e38 call: pre-jitter pos and vel (the inputs of $203f0), the jittered position, the appended object record
         field by field (x y z vx vy vz life handler), nobj growth, RNG after the spawn (64 bits), RNG at the return of $22e38
         (no further draw), and that the actor record fire_in saw is the record in the next arrival's actor pool (the fire
         "does not change the record"); a record found in the next arrival's object pool.
handler: per $20310 entry: the walker's flight (entry registers = model of the stored record), the stored record at $20378,
         the outcome class (from which breakpoints the pass reached), the fuel after a hit and $62a5d, the map byte after a
         fresh object hit, and the successor: a flying record is in the next arrival's pool, a removed one is not.
life:    every enemy-shot record of every arrival's object pool: life >= 1 gets exactly one handler entry in the tick with
         the record as its stored copy, life 0 gets none and is gone at the next arrival.
Controls (--control): mshift, nomuzzle, jit13, draw4, life21 (spawn); box50, cost332, nograv, far180 (handler).
"""
import json, os, struct, sys, collections
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import eshot as E
S = E.S
s16 = S.s16
MULTI = 150000
SKIPPED = collections.Counter()
CALLERS = collections.Counter()
TALLY = collections.OrderedDict()
BAD = collections.defaultdict(list)


def chk(name, ok, info=None):
    t = TALLY.setdefault(name, [0, 0]); t[1] += 1
    if ok:
        t[0] += 1
    elif len(BAD[name]) < 3:
        BAD[name].append(info)
    return ok


def obj_unpack(h):
    return list(struct.unpack('>7hL', bytes.fromhex(h)))


def pool_objs(raw):
    if not raw:
        return []
    b = bytes.fromhex(raw)
    return [tuple(struct.unpack('>7hL', b[i:i + 18])) for i in range(0, len(b), 18)]


def pool_actors(raw):
    if not raw:
        return []
    b = bytes.fromhex(raw)
    return [tuple(struct.unpack('>8hL', b[i:i + 20])) for i in range(0, len(b), 20)]


def rng_of(h):
    return struct.unpack('>2L', bytes.fromhex(h))


def run(path, control):
    cap = json.load(open(path)); rows = cap['rows']
    import exact
    for k, r in enumerate(rows):
        nxt = rows[k + 1] if k + 1 < len(rows) else None
        # a row whose run from arrival to arrival took more than MULTI steps holds several game frames (ship death and respawn):
        # the pool at the arrival is not the pool of each pass, so the pool-based checks skip it (and the row before it)
        multi = r['tick_steps'] > MULTI
        if multi: SKIPPED['multi-frame row (pool checks skipped)'] += 1
        if nxt and nxt['tick_steps'] > MULTI: nxt = None
        ev = r['ev']
        nobj_next = pool_objs(nxt['obj']) if nxt else None
        act_next = pool_actors(nxt['pool']) if nxt else None
        hs0 = [j for j, e in enumerate(ev) if e['e'] == 'h_in']
        entries = [(ev[j], None, obj_unpack(ev[j]['mem'])) for j in hs0]
        # ---------------- fire
        i = 0
        while i < len(ev):
            e = ev[i]
            if e['e'] != 'fire_in':
                i += 1; continue
            rec = list(struct.unpack('>8hL', bytes.fromhex(e['rec'])))
            mat = [struct.unpack('>h', bytes.fromhex(e['mat'])[o:o + 2])[0] for o in (0, 6, 12)]
            rng = rng_of(e['rng'])
            has_spawn = i + 1 < len(ev) and ev[i + 1]['e'] == 'spawn_in'
            crash = e['crash']
            chk('fire/crash path: no spawn when $62a5e set', has_spawn == (not crash))
            pre, npos, obj, rng2 = E.fire_step(rec, mat, crash, rng, e['nobj'], control)
            if not has_spawn:
                i += 1; continue
            si, so, fo = ev[i + 1], ev[i + 2], ev[i + 3]
            assert so['e'] == 'spawn_out' and fo['e'] == 'fire_out', [x['e'] for x in ev[i:i + 4]]
            chk('spawn/rng before spawn_in = fire_in', rng_of(si['rng']) == rng)
            for n, (a, b) in zip('xyz', zip(pre[0], si['d'])):
                chk(f'spawn/pre pos {n}', (a & 0xffff) == b, (a, b))
            for n, (a, b) in zip(('vx', 'vy', 'vz'), zip(pre[1], si['a'])):
                chk(f'spawn/pre vel {n}', (a & 0xffff) == b, (a, b))
            for n, (a, b) in zip('xyz', zip(npos, so['d'])):
                chk(f'spawn/jittered pos {n}', (a & 0xffff) == b, (a, b))
            chk('spawn/rng after $203f0 (3 draws)', rng2 == rng_of(so['rng']), (rng2, so['rng']))
            chk('spawn/rng at return of $22e38 (no more draws)', rng_of(fo['rng']) == rng_of(so['rng']))
            grew = so['nobj'] == e['nobj'] + 1
            chk('spawn/nobj grows by one iff below $177', grew == (obj is not None), (e['nobj'], so['nobj']))
            if grew and obj is not None:
                got = obj_unpack(so['rec'])
                for n, (a, b) in zip(('x', 'y', 'z', 'vx', 'vy', 'vz', 'life', 'handler'), zip(obj, got)):
                    chk(f'spawn/record {n}', a == b, (a, b))
                # the actor walker runs before the object walker: the new record is walked in the SAME tick (life 22 -> 21)
                walked = [m for (_h, _s, m) in entries if tuple(m) == tuple(got)]
                chk('spawn/record is walked by the object walker in the same tick (entry mem = record)', len(walked) == 1, (got, len(walked)))
            # the actor record is unchanged by the fire: it is the record of the next arrival's pool
            CALLERS[e['ret']] += 1
            if act_next is not None:
                pursuer = e['ret'] in (0x21fc2, 0x220de)
                n = 6 if pursuer else 3     # the patrol states go on steering and thrusting after the fire: position only
                # a patrol that this fire provoked is converted to $21f00 by $201b4 later in the same tick
                cands = [a for a in act_next if tuple(a[:n]) == tuple(rec[:n]) and (a[8] == rec[8] or (not pursuer and a[8] == 0x21f00))]
                chk('fire/%s actor record unchanged at the next arrival (%s)' % ('pursuer' if pursuer else 'patrol', 'x y z v' if pursuer else 'x y z only'),
                    len(cands) >= 1)
            i += 4
        # ---------------- handler
        hs = [j for j, e in enumerate(ev) if e['e'] == 'h_in']
        pool_k = pool_objs(r['obj'])
        entries = []
        for n, j in enumerate(hs):
            end = hs[n + 1] if n + 1 < len(hs) else len(ev)
            seg = {}
            for e2 in ev[j + 1:end]:
                if e2['e'].startswith('h_'):
                    seg.setdefault(e2['e'], e2)
                else:
                    break
            h = ev[j]
            mem = obj_unpack(h['mem'])
            entries.append((h, seg, mem))
            ship = struct.unpack('>3h', bytes.fromhex(h['ship']))
            crash = h['flags'] and bytes.fromhex(h['flags'])[1]
            gcap = (seg['h_gnd']['d1'], seg['h_gnd']['d3']) if 'h_gnd' in seg else None
            gnd = (lambda x, z: (s16(gcap[0]), gcap[1])) if gcap else (lambda x, z: (0, 0))
            res = E.handler_step(mem, ship, h['fuel'], crash, h['g'], gnd, h['cellbyte'], control)
            out = res['out']
            # the entry registers are the walker's output: pos + vel, life - 1
            x, y, z, vx, vy, vz, life, hh = mem
            for n2, (a, b) in zip(('x', 'y', 'z', 'vx', 'vy', 'vz', 'life'),
                                  zip((x + vx, y + vy, z + vz, vx, vy, vz, life - 1), h['dr'])):
                chk(f'handler/walker flight {n2}', (a & 0xffff) == b, (a, b))
            # observed class
            if 'h_hit' in seg: obs = 'hit'
            elif 'h_below' in seg: obs = 'ground' if 'h_xx' in seg else 'water'
            elif 'h_cell' in seg:
                # $203da is the btst/bne (always reached after the bset); $203de is the fall-through to $20218 (bit 5 clear)
                obs = 'wreck' if 'h_fresh' not in seg else ('fresh_plain' if 'h_plain' in seg else 'fresh_inf')
            else: obs = 'fly'
            chk('handler/outcome class', out == obs, (out, obs, mem))
            chk(f'handler/class={obs} predicted', out == obs)
            if 'stored' in res and 'h_miss' in seg:
                got = obj_unpack(seg['h_miss']['stored'])
                for n2, (a, b) in zip(('x', 'y', 'z', 'vx', 'vy', 'vz', 'life'), zip(res['stored'], got)):
                    chk(f'handler/stored record {n2}', a == b, (a, b))
            if obs == 'hit':
                chk('hit/fuel after ($32a2e)', res.get('fuel') == seg['h_rm_hit']['fuel'], (res.get('fuel'), seg['h_rm_hit']['fuel']))
                chk('hit/$62a5d', res.get('flag5d', 0) == seg['h_rm_hit']['f5d'])
                chk('hit/fuel before = fuel at h_hit', seg['h_hit']['fuel'] == h['fuel'])
            if obs in ('fresh_inf', 'fresh_plain'):
                ev3 = seg.get('h_plain') or seg.get('h_inf')
                chk('fresh/map byte after (bit 4 set)', res.get('cell') == ev3['cellbyte_after'], (res.get('cell'), ev3['cellbyte_after']))
            if 'h_cell' in seg:
                chk('wreck-or-fresh/type byte D6 = map byte & $1f', seg['h_cell']['d6'] & 0xff == h['cellbyte'] & 0x1f,
                    (seg['h_cell']['d6'], h['cellbyte']))
            if 'h_gnd' in seg and 'stored' in res:
                chk('ground/d6 = ground - y chooses below (D1 from $245b8)', ((s16(gcap[0]) - res['stored'][1]) < 0) == ('h_below' in seg))
            # ground model check, landscape 0 formula (exact.ground), by wave
            if gcap:
                gm = exact.ground(res['stored'][0], res['stored'][2])
                chk(f'info: ground height exact.ground (landscape 0 formula) = D1, wave {r["wave"]}', gm == s16(gcap[0]), (gm, gcap, r['wave']))
            # successor
            if nxt:
                st = tuple(res['stored'] + [E.HANDLER]) if 'stored' in res else None
                if st:
                    inpool = st in set(nobj_next)
                    chk(f'successor: stays iff fly (class {out})', inpool == (out == 'fly'))
        # ---------------- lifetime: each record of the arrival's pool
        stored_k = collections.Counter(tuple(m) for (_h, _s, m) in entries)
        for rec in ([] if multi else pool_objs(r['obj'])):
            if rec[7] != E.HANDLER:
                continue
            n = stored_k.get(tuple(rec), 0)
            if rec[6] >= 1:
                chk('life: life >= 1 record gets exactly one handler entry', n == 1, (rec, n))
            else:
                chk('life: life 0 record gets none', n == 0, (rec, n))
                if nxt:
                    chk('life: life 0 record gone at the next arrival', rec not in set(nobj_next))
        # every entry is a record of the arrival's pool or a record the actor walker spawned this tick
        poolset = set(pool_objs(r['obj']))
        spawned = [tuple(obj_unpack(e['rec'])) for e in ev if e['e'] == 'spawn_out' and e['rec'] and e['nobj'] > 0]
        for (_h, _s, m) in ([] if multi else entries):
            chk('handler entry = record of the arrival pool or of this tick\'s spawn', tuple(m) in poolset or tuple(m) in spawned)


def main():
    args = sys.argv[1:]
    control = 'none'
    if '--control' in args:
        i = args.index('--control'); control = args[i + 1]; del args[i:i + 2]
    for p in args:
        run(p, control)
    for k, (a, b) in TALLY.items():
        print(f'  {k:78s} {a}/{b}' + ('' if a == b or k.startswith('info:') else '  <-- MISMATCH'))
        if a != b and not k.startswith('info:'):
            for x in BAD[k]:
                print('      e.g.', x)
    print('  skipped:', dict(SKIPPED))
    print('  callers of $22e38:', {hex(k): v for k, v in sorted(CALLERS.items())})
    TALLY2 = {k: v for k, v in TALLY.items() if not k.startswith('info:')}
    tot = [sum(v[0] for v in TALLY2.values()), sum(v[1] for v in TALLY2.values())]
    print('== control' if control != 'none' else '== model', control, 'checks', tot[0], '/', tot[1],
          'failing groups', sum(1 for v in TALLY2.values() if v[0] != v[1]))


main()
