"""Natural (unpoked) capture of the enemy shot: the fire routine $22e38, the spawn $203f0 and the handler $20310.

    uv run python cap_eshot.py <snapshot> <ticks> <out.json>

Per arrival at $255d4 a row (ship, RNG, fuel, flags, object pool, tick counters, wave) and the ordered events of the tick:
  fire_in   $22e38 entry:   A3 record (20 bytes), A1 matrix words +0,+6,+12, $62a5e, RNG, nobj, caller
  spawn_in  $203f0 entry:   D0-D2, A0-A2, RNG, nobj
  spawn_out $22e76:         RNG, nobj, the last object record, D0-D2
  fire_out  $22eb8:         RNG, nobj
  h_in      $20310 entry:   D0-D6, the stored record at A6-18 (before the walker's update is written back), ship, fuel, flags, nobj
  h_hit $20354 / h_fuel0 $20360 / h_rm_hit $20374 (fuel after) / h_miss $20378 (stored record) / h_gnd $20382 (D1, D3)
  h_below $203e2 / h_cell $203cc (type byte) / h_fresh $203d0 / h_inf $203da / h_plain $203de / h_xx $203ea
Writes only <out.json>.  A re-stop (an interrupt taken at the breakpoint) is recognised by identical registers.
"""
import json, os, struct, sys, time
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
d = here
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
ROOT = d
sys.path.insert(0, os.path.join(ROOT, 'reversing/virus/py/mpc'))
import replay as R

TICK = R.TICK
EV = {0x22e38: 'fire_in', 0x203f0: 'spawn_in', 0x22e76: 'spawn_out', 0x22eb8: 'fire_out', 0x20310: 'h_in',
      0x20354: 'h_hit', 0x20360: 'h_fuel0', 0x20374: 'h_rm_hit', 0x20378: 'h_miss', 0x20382: 'h_gnd',
      0x203e2: 'h_below', 0x203cc: 'h_cell', 0x203d0: 'h_fresh', 0x203da: 'h_inf', 0x203de: 'h_plain', 0x203ea: 'h_xx'}
hx = R.hx
hm_seen = {}


def capture(snap, N, cap=8000000):
    g = R.Game(snap)
    s = g.s
    rd = lambda a, n: s('read', addr=a, len=n)
    rows = []
    try:
        s('bp_set', addrs=list(EV))
        ok, path, ext, _, steps, why = g.run_to_tick(3000000)
        assert ok, why
        for k in range(N):
            regs, st = g.state()
            st['rng'] = rd(0x2706e, 8)
            c = bytes.fromhex(rd(0x32a3c, 22))
            st['nobj'], st['npool'] = struct.unpack('>2h', c[:4])
            st['tick44'], = struct.unpack('>H', c[8:10]); st['tick48'], = struct.unpack('>H', c[12:14])
            st['wave'], = struct.unpack('>h', c[20:22])
            st['obj'] = rd(0x302f6, 18 * st['nobj']) if st['nobj'] > 0 else ''
            st['pool'] = rd(0x31d54, 20 * st['npool']) if st['npool'] > 0 else ''
            if st['wave'] not in hm_seen:
                hm_seen[st['wave']] = rd(0x42a58, 0x10000)
            ev = []; tot = 0; done = False; last = None
            while not done:
                r = s('run', max_steps=cap)
                tot += r['steps']
                if r['reason'] != 'breakpoint':
                    st['stopped'] = r['reason']; done = True; break
                pc = hx(r['pc'])
                rg = s('regs')
                key = (pc, tuple(rg[x] for x in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6')))
                if key == last:
                    continue                                   # interrupt taken at the breakpoint: same arrival
                last = key
                if pc == TICK:
                    if tot < 64 and not ev:
                        last = None; continue
                    break
                name = EV.get(pc)
                if name is None:
                    continue
                e = {'e': name}
                D = lambda n: hx(rg[n]) & 0xffff
                if name == 'fire_in':
                    a1 = hx(rg['a1']); a3 = hx(rg['a3'])
                    e['rec'] = rd(a3, 20); e['mat'] = rd(a1, 14); e['a1'] = a1; e['a3'] = a3
                    e['crash'] = hx(rd(0x62a5e, 1)); e['rng'] = rd(0x2706e, 8)
                    e['nobj'] = struct.unpack('>h', bytes.fromhex(rd(0x32a3c, 2)))[0]
                    e['ret'] = hx(rd(hx(rg['a7']), 4))
                elif name == 'spawn_in':
                    e['d'] = [D('d0'), D('d1'), D('d2')]; e['a'] = [D('a0'), D('a1'), D('a2')]
                    e['rng'] = rd(0x2706e, 8)
                    e['nobj'] = struct.unpack('>h', bytes.fromhex(rd(0x32a3c, 2)))[0]
                elif name in ('spawn_out', 'fire_out'):
                    e['rng'] = rd(0x2706e, 8)
                    e['nobj'] = struct.unpack('>h', bytes.fromhex(rd(0x32a3c, 2)))[0]
                    if name == 'spawn_out':
                        e['d'] = [D('d0'), D('d1'), D('d2')]
                        e['rec'] = rd(0x302f6 + 18 * (e['nobj'] - 1), 18) if e['nobj'] > 0 else ''
                elif name == 'h_in':
                    a6 = hx(rg['a6'])
                    e['dr'] = [D(x) for x in ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6')]
                    e['mem'] = rd(a6 - 18, 18); e['slot'] = (a6 - 18 - 0x302f6) // 18
                    e['ship'] = rd(0x270b0, 6); e['fuel'] = struct.unpack('>H', bytes.fromhex(rd(0x32a2e, 2)))[0]
                    e['flags'] = rd(0x62a5d, 2); e['nobj'] = struct.unpack('>h', bytes.fromhex(rd(0x32a3c, 2)))[0]
                    e['g'] = struct.unpack('>h', bytes.fromhex(rd(0x32a3a, 2)))[0]
                    xx, zz = D('d0'), D('d2')           # the object-map cell the handler will test ($203a0..$203be)
                    cell = (((xx + 0x80) & 0xffff) >> 8) + (((zz + 0x80) & 0xffff) & 0xff00)
                    e['cellbyte'] = hx(rd(0x32a58 + cell, 1))
                elif name == 'h_rm_hit':
                    e['fuel'] = struct.unpack('>H', bytes.fromhex(rd(0x32a2e, 2)))[0]; e['f5d'] = hx(rd(0x62a5d, 1))
                elif name == 'h_hit':
                    e['fuel'] = struct.unpack('>H', bytes.fromhex(rd(0x32a2e, 2)))[0]
                elif name == 'h_miss':
                    a6 = hx(rg['a6']); e['stored'] = rd(a6 - 18, 18)
                elif name == 'h_gnd':
                    e['d1'] = D('d1'); e['d3'] = D('d3')
                elif name == 'h_below':
                    e['d3'] = D('d3'); e['d5'] = D('d5'); e['d6'] = D('d6'); e['d1'] = D('d1')
                elif name in ('h_inf', 'h_plain'):
                    e['cellbyte_after'] = hx(rd(hx(rg['a3']), 1)); e['a3'] = hx(rg['a3'])
                elif name == 'h_cell':
                    e['d6'] = D('d6'); e['d1'] = D('d1'); e['d5'] = D('d5')
                ev.append(e)
            st['ev'] = ev; st['tick_steps'] = tot
            rows.append(st)
            if done:
                print('stopped at tick', k, st.get('stopped')); break
        return {'snap': snap, 'rows': rows, 'hmaps': hm_seen}
    finally:
        g.close()


if __name__ == '__main__':
    t0 = time.time()
    out = capture(sys.argv[1], int(sys.argv[2]))
    json.dump(out, open(sys.argv[3], 'w'))
    cnt = {}
    for r in out['rows']:
        for e in r['ev']:
            cnt[e['e']] = cnt.get(e['e'], 0) + 1
    print(len(out['rows']), 'ticks', round(time.time() - t0, 1), 's; events', cnt)
