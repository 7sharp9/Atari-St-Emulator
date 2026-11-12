#!/usr/bin/env python3
"""Prove the Manta take-off model (slot state +28 = 2, $1d22c) against the emulator, tick by tick.

usage: takeoff_proof.py <snap> [addr=value:width ...]

From <snap> (c_s30.snap: Manta 0 in the hangar), the pokes are applied, Manta 0 is sent up the lift with the game's
own command handler ($11386), the run waits for the lift to stop with the Manta on deck (+28 = 1, $dca = 0), and the
launch handler ($11af6) is called. Then, at every entry of the Manta update $1cab4 (one per main frame), the state
of slot 0 ($498) and its entity ($5df5a) is read; the model predicts each entry from the one before, through the
three take-off phases and the hand-off to flight (+28 = 3). The carrier is an input: its position, heading and
speed are read at the earlier entry, because the Manta update runs after the carrier's in the same frame.
Prints one line per mismatching field and 'takeoff ticks N match M'.
"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
from ccpaths import *
import struct

sys.path.insert(0, str(ROOT / 'tools'))
from stclient import StServer

SIN = [struct.unpack('>h', ram()[0x1864 + 2 * i:0x1866 + 2 * i])[0] for i in range(4096)]   # render.md section 2


def s16(v):
    v &= 0xffff
    return v - 65536 if v & 0x8000 else v


def u16(v): return v & 0xffff


P0 = dict(rise=2, rise_top=200, accel=8, vmax=0x3c, roll_end=0x28a, pitch_rate=0xf0, pitch_floor=0xf989, climb=10,
          deck_end=0x7d0, pitch_div=-14, add_carrier=1, follow_heading=1, inverse=1)
P = dict(P0)


def deck_to_world(dx, dz, heading, cx, cz):
    """$1d908: $9f76 stores (sin, cos) of the carrier heading, $a0a4 rotates the deck offset back, then the carrier
    position is added."""
    h = heading & 0xfff0
    s, c = SIN[h >> 4], SIN[((h + 0x4000) & 0xffff) >> 4]
    sg = 1 if P['inverse'] else -1
    x = s16(((dx * c + sg * dz * s) * 4) >> 16)
    z = s16(((dz * c - sg * dx * s) * 4) >> 16)
    return cx + x, cz + z


def step(a):
    """The state at the next $1cab4 entry, from the state at this one (slot 0 in take-off, +28 = 2)."""
    b = dict(a)
    ph = a['phase']
    if ph == 0:                                     # $1d250: rise off the lift
        b['alt'] = a['alt'] + P['rise']
        if u16(b['alt']) >= P['rise_top']:                    # cmp.l #$c8 / bcs
            b['phase'] = 1
            b['v'] = 0                              # clr.w 6(A1)
    elif ph == 1:                                   # $1d280: roll along the deck
        v = u16(a['v'] + P['accel'])
        if v > P['vmax']: v = P['vmax']                       # bls: unsigned
        b['v'] = v
        b['dz'] = s16(a['dz'] + v)
        if u16(b['dz']) >= P['roll_end']:
            b['phase'] = 2
    else:                                           # $1d2c2: rotate and climb off the bow
        p = s16(a['pitch'] - P['pitch_rate'])
        if p <= s16(P['pitch_floor']): p = s16(P['pitch_floor'])        # bgt: signed floor
        b['pitch'] = p
        b['alt'] = a['alt'] + P['climb']
        b['dz'] = s16(a['dz'] + a['v'])
        if u16(b['dz']) >= P['deck_end']:                   # $1d2f8: airborne
            b['s2'] = 0
            b['s4'] = s16(int(p / P['pitch_div']))             # divs #$fff2: truncates toward zero
            b['v'] = s16(a['v'] + P['add_carrier'] * a['cv'])          # plus the carrier's speed $646
            b['s8'] = b['v']
            b['state'] = 3
    b['heading'] = a['cheading'] if P['follow_heading'] else a['heading']                    # move.w $5e960,6(A4)
    b['x'], b['z'] = deck_to_world(b['dx'], b['dz'], a['cheading'], a['cx'], a['cz'])
    return b


def read(s):
    sl = s.read(0x498, 52)
    e = s.read(0x5df5a, 32)
    c = s.read(0x5e95a, 22)
    h = lambda b, o: struct.unpack('>h', b[o:o + 2])[0]
    l = lambda b, o: struct.unpack('>l', b[o:o + 4])[0]
    return dict(state=sl[28], phase=sl[29], v=h(sl, 6), s2=h(sl, 2), s4=h(sl, 4), s8=h(sl, 8),
                alt=l(e, 14), pitch=h(e, 4), heading=struct.unpack('>H', e[6:8])[0], dx=h(e, 28), dz=h(e, 30),
                x=l(e, 10), z=l(e, 18),
                cheading=struct.unpack('>H', c[6:8])[0], cx=l(c, 10), cz=l(c, 18),
                cv=struct.unpack('>h', s.read(0x646, 2))[0])


FIELDS = ['state', 'phase', 'v', 'alt', 'pitch', 'heading', 'dx', 'dz', 'x', 'z']
HANDOFF = ['s2', 's4', 's8']


def main():
    snap = sys.argv[1]
    s = StServer(str(ROOT))
    s('load', snapshot=snap)
    s('poke', addr=0x126c, width=4, value=0x00ff0001)          # the crack's stack leak (README "Provenance")
    for p in sys.argv[2:]:
        addr, rest = p.split('=')
        val, width = rest.split(':')
        s('poke', addr=int(addr, 16), width=int(width), value=int(val, 16))

    w = lambda a: struct.unpack('>h', s.read(a, 2))[0]
    s.call_resume(0x11386, d2=2)                                    # Manta 0 up the lift
    s('bp_set', addrs=[0x1cab4])
    for k in range(400):
        r = s('run', max_steps=400000)
        assert r['reason'] == 'breakpoint', r
        if s.read(0x498 + 28, 1)[0] == 1 and w(0xdca) == 0:
            break
    else:
        sys.exit('the Manta never reached the deck')
    print(f'on deck after {k + 1} ticks')
    s('bp_clear', addrs=[0x1cab4])
    s.call_resume(0x11af6, d2=2)                                    # launch
    s('bp_set', addrs=[0x1cab4])
    S = []
    for k in range(200):
        r = s('run', max_steps=400000)
        assert r['reason'] == 'breakpoint', r
        S.append(read(s))
        if S[-1]['state'] != 2:
            break
    s('bp_clear', addrs=[0x1cab4])
    s.close()
    assert S[0]['state'] == 2 and S[0]['phase'] == 0, S[0]
    n = len(S) - 1

    def score(verbose):
        ok = 0
        for k in range(n):
            p, g = step(S[k]), S[k + 1]
            names = FIELDS + (HANDOFF if g['state'] == 3 else [])
            bad = [f for f in names if p[f] != g[f]]
            if bad and verbose:
                print(f'tick {k + 1}: ' + ', '.join(f'{f} model {p[f]} game {g[f]}' for f in bad))
            ok += not bad
        return ok
    ok = score(True)
    ph = [x['phase'] for x in S]
    print(f'phases {ph.count(0)}/{ph.count(1)}/{ph.count(2)} entries; airborne at tick {n} with speed '
          f'{S[-1]["v"]}, pitch {S[-1]["pitch"]}, carrier speed {S[-2]["cv"]}, carrier heading '
          f'{S[0]["cheading"]:#06x}..{S[-1]["cheading"]:#06x}')
    # controls: each constant nudged in turn must break at least one tick
    broke = 0
    for key, base in P0.items():
        P.clear(); P.update(P0)
        P[key] = (1 - base) if key in ('add_carrier', 'follow_heading', 'inverse') else base + (1 if base > 0 else -1)
        m = score(False)
        broke += m < n
        print(f'  control {key} = {P[key]}: {m}/{n}')
    P.clear(); P.update(P0)
    print(f'controls broken {broke}/{len(P0)}')
    # a threshold crossed in one 60-unit step is pinned by the data only to that step's interval
    for key, ph0, done in (('roll_end', 1, lambda x: x['phase'] == 2), ('deck_end', 2, lambda x: x['state'] == 3)):
        lo = max(S[k + 1]['dz'] for k in range(n) if S[k]['phase'] == ph0 and S[k + 1]['phase'] == ph0
                 and S[k + 1]['state'] == 2)
        hi = [S[k + 1]['dz'] for k in range(n) if S[k]['phase'] == ph0 and done(S[k + 1])][0]
        print(f'  {key} {P0[key]} bounded by the data to ({lo}, {hi}]')
    print(f'takeoff ticks {n} match {ok}')

if __name__ == '__main__':
    main()
