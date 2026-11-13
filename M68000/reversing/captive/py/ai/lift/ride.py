"""Leg A: ride a lift by input and account for every plane-2 and tile change: ride.py <snap> <out.snap> <segment ...>
segment = <label>=<input>[+<input>...] with inputs as in drive.py (k<hex>, c<x>:<y>, w<steps>). For each segment:
party position, facing, floor word 15688(A6), 46/48(A6); hit counts of the lift, step and occupancy routines; every
CPU write to plane 2 ($1e208-$1ea07) by PC other than the four seen-mark writers $86a0/$86ae/$86bc/$86ca; and the
plane-2 diff over the segment (whole byte, and bits 3-5 alone) and the tile-layer diff."""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe_input as P
from probe_input import srv, w16, A6  # noqa
P.ADDRS.clear()
P.ADDRS.update({a: f'{a:x}' for a in (0x969a, 0x9768, 0x977c, 0x902e, 0x906a, 0x90d0, 0x90e2, 0x8652, 0x867e, 0x9116,
                                      0x10f20, 0x88b8, 0x88d6, 0x9772, 0x9786, 0x9792, 0x9332, 0x9336, 0xf884)})
SEEN = {'$0086a0', '$0086ae', '$0086bc', '$0086ca'}
s = srv(sys.argv[1])
wid = s('watch_add', lo='$1e208', hi='$1ea07', kind='w', max_events=200000)['id']
P2, GR = A6 + 11322, A6 + 9242
for seg in sys.argv[3:]:
    label, inputs = seg.split('=')
    p0, g0 = s.read(P2, 2048), s.read(GR, 2048)
    pos0 = (w16(s, 26), w16(s, 28), w16(s, 30), w16(s, 15688))
    s('watch_events', id=wid)  # drain
    tot = dict.fromkeys(P.ADDRS, 0)
    for inp in inputs.split('+'):
        P.run(s, int(inp[1:]), tot) if inp[0] == 'w' else P.drive(s, inp, tot)
    p1, g1 = s.read(P2, 2048), s.read(GR, 2048)
    ev = s('watch_events', id=wid); ev = ev[0] if isinstance(ev, list) else ev
    wr = collections.Counter((e['pc'], e['addr'], e['value']) for e in ev['events'] if e['pc'] not in SEEN)
    cell = lambda i: (i % 64, i // 64)
    d_all = [(cell(i), f'{p0[i]:02x}>{p1[i]:02x}') for i in range(2048) if p0[i] != p1[i]]
    d35 = [(cell(i), (p0[i] >> 3) & 7, (p1[i] >> 3) & 7) for i in range(2048) if (p0[i] ^ p1[i]) & 0x38]
    d_low = [(cell(i), f'{p0[i]:02x}>{p1[i]:02x}') for i in range(2048) if (p0[i] ^ p1[i]) & 0x7f]
    dg = [(cell(i), f'{g0[i]:02x}>{g1[i]:02x}') for i in range(2048) if g0[i] != g1[i]]
    print(f'[{label}] {inputs}: pos {pos0[:2]} face {pos0[2]} fl {pos0[3]} -> pos ({w16(s, 26)}, {w16(s, 28)}) face '
          f'{w16(s, 30)} fl {w16(s, 15688)}; 46/48(A6) {w16(s, 46)} {w16(s, 48)}')
    print('  hits', {P.ADDRS[a]: n for a, n in tot.items()})
    print('  plane-2 writers other than the seen marks', dict(wr))
    print(f'  plane 2: bits 3-5 changed {len(d35)}/2048 {d35}; bits 0-6 changed {len(d_low)} {d_low}')
    print(f'  plane 2 whole-byte changes {len(d_all)} (bit 7 = seen marks): {d_all}')
    print(f'  tile layer changes {len(dg)}: {dg}', flush=True)
s('save', path=os.path.abspath(sys.argv[2])); s.close()
