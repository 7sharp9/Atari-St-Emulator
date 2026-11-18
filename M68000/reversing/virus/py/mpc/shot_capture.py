"""Capture a run of Virus from demo/S1b.snap for the shot/target gates: per arrival at $255d4 the ship, RNG, score,
object pool ($302f6, 18-byte records), actor pool ($31d54, 20-byte records), and the events of the tick that follows
(breakpoints inside the fire code, the player's shot handler, the actor kill path and the ship-hit store).

    uv run python shot_capture.py <policy> <ticks> <out.json>

policy: auto (the game's autopilot untouched) | autofire (autopilot D0/D1, fire bit forced on every tick)
      | nofire (autopilot, fire bit cleared)
      | wobble (autopilot D0/D1 plus a fixed small offset pattern, fire forced) | file:<controls.json>
Writes only <out.json>. 
"""
import json, os, struct, sys, time
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import replay as R

TICK = R.TICK
EV = {
    0x2578e: 'fire_pre',     # before jsr $202fc: D0-2 nominal pos, A0-2 nominal vel
    0x25794: 'fire_post',    # after: the appended record is the last one
    0x1ff06: 'hit',          # player's shot inside an actor's box: A0 = actor record
    0x1ff6e: 'obj_fresh',    # shot over an undestroyed object cell
    0x1ff80: 'below',        # shot below the ground height
    0x1ff8a: 'boom',         # explosion path (object already destroyed, or ground)
    0x1fe36: 'water',        # splash
    0x1ffc8: 'award40',      # infected object of type < 4
    0x20232: 'award1000',    # object type $c
    0x1fc58: 'h_remove',     # a handler removes its record (any handler)
    0x216d6: 'kill',         # actor kill with award A0
    0x21654: 'ship_hit',     # the common tail found the ship inside the actor's box
    0x25ad8: 'dead',
}
MAP_LO, MAP_HI = 0x32a58, 0x42a57


def hx(v): return int(str(v).lstrip('$'), 16)


def policy_fn(name):
    if name == 'auto':
        return lambda k, d: None
    if name == 'autofire':
        return lambda k, d: [d[0], d[1], d[2] | 1]
    if name == 'nofire':
        return lambda k, d: [d[0], d[1], d[2] & ~1]
    if name == 'wobble':
        def f(k, d):
            o0 = ((k * 37) % 9 - 4) * 0x80
            o1 = ((k * 53) % 11 - 5) * 0x100
            return [max(0, min(0x7fff, d[0] + o0)), (d[1] + o1) & 0xffff, d[2] | 1]
        return f
    if name.startswith('file:'):
        seq = json.load(open(name[5:]))
        return lambda k, d: (seq[k] if k < len(seq) else None)
    raise SystemExit('unknown policy ' + name)


def capture(policy, N, snap=None, hook=None, cap=8000000):
    """hook(g, k, row) may poke the machine at arrival k before the tick runs (after the reads); returns nothing."""
    snap = snap or os.path.join(R.ROOT, 'scratchpad/virus/demo/S1b.snap')
    pol = policy_fn(policy) if isinstance(policy, str) else policy
    g = R.Game(snap)
    s = g.s
    rd = lambda a, n: s('read', addr=a, len=n)
    rows = []
    try:
        s('bp_set', addrs=list(EV))
        wid = s('watch_add', lo=MAP_LO, hi=MAP_HI, kind='w', source='cpu', max_events=200000)['id']
        ok, path, ext, _, steps, why = g.run_to_tick(3000000)
        assert ok, why
        s('watch_events', id=wid)                       # drop the writes before tick 0
        map0 = rd(MAP_LO, 0x10000)
        hmap = rd(0x42a58, 0x10000)
        for k in range(N):
            regs, st = g.state()
            st['rng'] = rd(0x2706e, 8)
            st['score'] = struct.unpack('>l', bytes.fromhex(rd(0x2708e, 4)))[0]
            c = bytes.fromhex(rd(0x32a3c, 22))          # nobj, npool, $32a40.. $32a44 tick, $32a48, $32a50 wave
            st['nobj'], st['npool'] = struct.unpack('>2h', c[:4])
            st['tick44'], = struct.unpack('>H', c[8:10]); st['tick48'], = struct.unpack('>H', c[12:14])
            st['wave'], = struct.unpack('>h', c[20:22])
            st['obj'] = rd(0x302f6, 18 * st['nobj']) if st['nobj'] > 0 else ''
            st['pool'] = rd(0x31d54, 20 * st['npool']) if st['npool'] > 0 else ''
            st['queue'] = rd(0x27134, 24); st['matrix'] = rd(0x270d4, 18); st['shippt'] = rd(0x270bc, 6)
            st['cam'] = rd(0x270ce, 6)
            if hook:
                hook(g, k, st)
                regs = s('regs')
            u = pol(k, st['d'])
            if u is not None:
                g.set_controls(regs, u)
                st['u'] = [int(v) & 0xffff for v in u]
            else:
                st['u'] = None
            ev = []; tot = 0; done = False; last_pc = None; since = 0
            while not done:
                r = s('run', max_steps=cap)
                tot += r['steps']; since = r['steps']
                if r['reason'] != 'breakpoint':
                    st['stopped'] = r['reason']; done = True; break
                pc = hx(r['pc'])
                if pc == last_pc and since < 64:        # an interrupt taken at the breakpoint address: re-arrival
                    continue
                last_pc = pc
                if pc == TICK:
                    if tot < 64 and not ev:
                        last_pc = None
                        continue
                    break
                name = EV.get(pc)
                if name is None:
                    ev.append({'e': R.PATHS.get(pc, hex(pc))}); continue
                e = {'e': name}
                if name in ('fire_pre', 'fire_post'):
                    rg = s('regs')
                    e['rng'] = rd(0x2706e, 8)
                    e['nobj'] = struct.unpack('>h', bytes.fromhex(rd(0x32a3c, 2)))[0]
                    if name == 'fire_pre':
                        e['regs'] = [hx(rg[x]) & 0xffff for x in ('d0', 'd1', 'd2', 'a0', 'a1', 'a2')]
                        e['d345'] = [hx(rg[x]) & 0xffff for x in ('d3', 'd4', 'd5')]
                        e['matrix'] = rd(0x270d4, 18)
                    else:
                        e['rec'] = rd(0x302f6 + 18 * (e['nobj'] - 1), 18)
                elif name == 'hit':
                    rg = s('regs')
                    a0 = hx(rg['a0']); a6 = hx(rg['a6'])
                    e['idx'] = (a0 - 0x31d54) // 20
                    e['actor'] = rd(a0, 20); e['shot'] = rd(a6 - 18, 18)
                    e['pool'] = rd(0x31d54, 20 * struct.unpack('>h', bytes.fromhex(rd(0x32a3e, 2)))[0])
                elif name in ('h_remove', 'obj_fresh', 'below', 'boom', 'water', 'award40', 'award1000'):
                    rg = s('regs')
                    a6 = hx(rg['a6'])
                    e['rec'] = rd(a6 - 18, 18)
                    e['d'] = [hx(rg[x]) & 0xffff for x in ('d0', 'd1', 'd2', 'd3', 'd5', 'd6')]
                    if name == 'obj_fresh':
                        e['cell'] = hx(rg['a3']); e['byte'] = rd(hx(rg['a3']), 1)
                    if name == 'h_remove' and int(e['rec'][28:], 16) != 0x1feb0:
                        continue                        # another handler's removal
                elif name == 'kill':
                    rg = s('regs')
                    a6 = hx(rg['a6'])
                    e['award'] = hx(rg['a0']) & 0xffff; e['rec'] = rd(a6 - 20, 20)
                    e['idx'] = (a6 - 20 - 0x31d54) // 20
                elif name == 'ship_hit':
                    rg = s('regs')
                    a6 = hx(rg['a6'])
                    e['rec'] = rd(a6 - 20, 20); e['idx'] = (a6 - 20 - 0x31d54) // 20
                    e['d'] = [hx(rg[x]) & 0xffff for x in ('d0', 'd1', 'd2', 'd4', 'd5', 'd7')]
                    e['shippt'] = rd(0x270bc, 6); e['ship'] = rd(0x270b0, 12); e['cam'] = rd(0x270ce, 6)
                ev.append(e)
            st['ev'] = ev; st['tick_steps'] = tot
            w = s('watch_events', id=wid)
            wl = [x for o in (w if isinstance(w, list) else [w]) for x in o.get('events', [])]
            if any(o.get('dropped') for o in (w if isinstance(w, list) else [w])): st['mapw_dropped'] = True
            st['mapw'] = [[hx(x['addr']), x['width'], hx(x['value'])] for x in wl]
            rows.append(st)
            if done:
                print('stopped at tick', k, st.get('stopped')); break
        map1 = rd(MAP_LO, 0x10000)
        _regs, last = g.state()
        return {'policy': policy if isinstance(policy, str) else 'fn', 'snap': snap, 'rows': rows, 'map0': map0,
                'map1': map1, 'hmap': hmap}
    finally:
        g.close()


if __name__ == '__main__':
    t0 = time.time()
    out = capture(sys.argv[1], int(sys.argv[2]))
    json.dump(out, open(sys.argv[3], 'w'))
    rows = out['rows']
    cnt = {}
    for r in rows:
        for e in r['ev']:
            cnt[e['e']] = cnt.get(e['e'], 0) + 1
    print(len(rows), 'ticks', round(time.time() - t0, 1), 's; events', cnt, 'final score', rows[-1]['score'],
          'npool', rows[-1]['npool'])
