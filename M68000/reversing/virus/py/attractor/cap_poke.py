"""Labelled-poke captures for the attractor's pull, fuel drain and kill paths (the natural corpus holds the pull and the drain;
it holds no ground kill and no ship contact).

    uv run python cap_poke.py <snapshot> <ticks> <out.json> <mode> [poke_tick]

Modes (every poke is made ONCE at poke_tick, default 10, the first live attractor `$224a6` of the pool is the target; the row of
that tick is rewritten to the poked state, so the gate reads it as the machine's state; row['poke'] labels it):
  none    no poke (same-snapshot control)
  near    ship position := attractor + (+$200, -$100, +$100): D3 about $500, inside the drain range $700
  far     ship position := attractor + (+$400, +$200, +$200): D3 $800, pull range only ($700 < D3 <= $b00)
  touch   ship position := attractor + ($20, $20, $20): inside the $c0 box of the common tail `$215ea` (ship contact)
  ground  attractor y := ground + $20 (the walker ors $a000 into the life word: ground kill)
Each row also carries 'fuelw': writes to $32a2e seen during that tick ([pc, width, value]) from a CPU watch (watch 32a2e 2)."""
import json, os, struct, sys, time
d = os.path.dirname(os.path.abspath(__file__)); R_ = d
while not os.path.exists(os.path.join(R_, 'tools', 'rdis.py')):
    R_ = os.path.dirname(R_)
sys.path.insert(0, os.path.join(R_, 'reversing/virus/py/mpc'))
import shot_capture as C
import shot as S
snap, N, out, mode = sys.argv[1:5]
N = int(N); PK = int(sys.argv[5]) if len(sys.argv) > 5 else 10
hm = {}; wid = [None]
w16 = lambda v: v & 0xffff

def hook(g, k, row):
    w = row['wave']
    if w not in hm:
        hm[w] = g.s('read', addr=0x42a58, len=0x10000)
        S._HMAP = bytes.fromhex(hm[w])
    row['hw'] = w
    if wid[0] is None:
        wid[0] = g.s('watch_add', lo=0x32a2e, hi=0x32a2f, kind='w', source='cpu', max_events=100000)['id']
    ev = g.s('watch_events', id=wid[0])
    evs = [x for o in (ev if isinstance(ev, list) else [ev]) for x in o.get('events', [])]
    row['fuelw'] = [[x.get('pc'), x['width'], int(str(x['value']).lstrip('$'), 16)] for x in evs]
    if k == PK and mode != 'none':
        P = S.unpack_pool(row['pool'])
        idx = [i for i, a in enumerate(P) if a[8] == 0x224a6]
        assert idx, 'no live attractor at the poke tick'
        i = idx[0]; a = P[i]
        row['poke'] = {'mode': mode, 'idx': i}
        if mode in ('near', 'far', 'touch'):
            off = {'near': (0x200, -0x100, 0x100), 'far': (0x400, 0x200, 0x200), 'touch': (0x20, 0x20, 0x20)}[mode]
            np_ = [S.s16(a[0] + off[0]), S.s16(a[1] + off[1]), S.s16(a[2] + off[2])]
            for ax in range(3):
                g.s('poke', addr=0x270b0 + 2 * ax, width=2, value=w16(np_[ax]))
            row['pos'] = np_
        elif mode == 'ground':
            gh = S.aground(a[0], a[2]); ny = S.s16(gh + 0x20)
            g.s('poke', addr=0x31d54 + 20 * i + 2, width=2, value=w16(ny))
            raw = bytearray(bytes.fromhex(row['pool'])); raw[20 * i + 2:20 * i + 4] = struct.pack('>h', ny)
            row['pool'] = raw.hex()
t0 = time.time()
c = C.capture('auto', N, snap=snap, hook=hook, cap=80000000)
for k in ('map0', 'map1', 'hmap'):
    c.pop(k)
c['hmaps'] = hm; c['mode'] = mode; c['poke_tick'] = PK
json.dump(c, open(out, 'w'))
print(mode, len(c['rows']), 'ticks', round(time.time() - t0), 's', 'last', c['rows'][-1].get('stopped'))
