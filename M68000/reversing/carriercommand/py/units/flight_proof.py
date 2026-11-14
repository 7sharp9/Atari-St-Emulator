#!/usr/bin/env python3
"""Prove the Manta's airborne autopilot (slot state +28 = 3, $1d354) and the shared flight code ($1ccb0..$1cf90)
against the emulator, tick by tick.

usage: flight_proof.py <snap> <ticks> [addr=value:width ...]

<snap> is m_takeoff.snap (Manta 0's first airborne tick; py/units/manta_snaps.py rebuilds it). The pokes are applied
after the crack fix (w 126c 00ff0001); use them to move the destination (slot +30/+38 longs at $4b6/$4be) or the
target altitude (+34 at $4ba). At every entry of the Manta update $1cab4 (one per main frame) slot 0 ($498) and its
entity ($5df5a) are read, and the model predicts each entry from the one before. The path modelled is the autopilot
one at altitude >= 150 with fuel left: $1d354 (steer), $1ce56 (fuel, only when $8fb is set: fuel is not checked
here), $1d880 (speed), $1d940 (attitude from the stick), $19e2e and $1cf58 (integrate). Prints one line per
mismatching field and 'flight ticks N match M', then a control per constant.
"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import struct
from atan_port import atan2

sys.path.insert(0, str(ROOT / 'tools'))
from stclient import StServer

SIN = [struct.unpack('>h', ram()[0x1864 + 2 * i:0x1866 + 2 * i])[0] for i in range(4096)]   # render.md section 2


def s16(v):
    v &= 0xffff
    return v - 65536 if v & 0x8000 else v


def s32(v):
    v &= 0xffffffff
    return v - (1 << 32) if v & 0x80000000 else v


def trunc_div(a, b):
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def sc(angle):
    k = (angle & 0xfff0) >> 4
    return SIN[k], SIN[(k + 1024) % 4096]


def rot_fwd(x, y, angle):                       # $a16c (render.md section 2, rot_gate.py)
    s, c = sc(angle)
    return s16(((x * c - y * s) * 4) >> 16), s16(((y * c + x * s) * 4) >> 16)


def rot_inv(x, y, angle):                       # $a12c
    s, c = sc(angle)
    return s16(((x * c + y * s) * 4) >> 16), s16(((y * c - x * s) * 4) >> 16)


def toward(cur, tgt, step):                     # $19e54: D1 moves toward D0 by at most D2 (unsigned compare)
    d = s16(tgt - cur)
    m = abs(d) & 0xffff
    if m > (step & 0xffff):
        m = step
    return s16(cur + (m if d >= 0 else -m))


def decay(v):                                   # $1e490: v - v/8, at least 1 toward 0
    if v == 0:
        return 0
    d = v >> 3
    if d == 0:
        d = 1
    return s16(v - d)


P0 = dict(alt_dead=20, alt_clamp=150, alt_rate=10, near=2000, near_speed=50, arrive=600, turn_div=10, stick_max=255,
          turn_rate=32, circle_alt=500, circle_pitch=150, circle_prate=20, circle_speed=70, circle_roll=128,
          circle_rrate=16, hull_shift=4, vmin=50, vmax_add=50, vmax_cap=250, accel=4, decel=16, roll_k=-25,
          pitch_k=-14, yaw_mul=16, yaw_div=6, alt_cap=3500)
P = dict(P0)


def step(a):
    """The state at the next $1cab4 entry from the state at this one (Manta 0, autopilot, +28 = 3, alt >= 150)."""
    b = dict(a)
    if b['c48']:
        b['c48'] -= 1
    # $1d354: steer
    if b['flags'] & 2:
        dalt = s16(a['talt'] - a['alt'])
        tgt = 0 if abs(dalt) < P['alt_dead'] else max(-P['alt_clamp'], min(P['alt_clamp'], dalt))
        b['s4'] = toward(a['s4'], tgt, P['alt_rate'])
        dx, dz = a['destx'] - a['x'], a['destz'] - a['z']
        d = max(abs(dx), abs(dz))
        b['s8'] = a['cruise']
        if d <= P['near']:
            b['s8'] = P['near_speed']
        if d >= P['arrive']:
            t = s16(atan2(dx, dz) - a['heading'])
            t = s16(trunc_div(t, P['turn_div']))
            t = max(-P['stick_max'], min(P['stick_max'], t))
            b['s2'] = toward(a['s2'], t, P['turn_rate'])
            circling = False
        else:                                   # $1d458: arrived, destination cleared, circle from here on
            b['flags'] &= ~2
            circling = True
    else:
        circling = True
    if circling:                                # $1d35c
        if a['alt'] > P['circle_alt']:
            b['s4'] = decay(b['s4'])
        else:
            b['s4'] = toward(b['s4'], P['circle_pitch'], P['circle_prate'])
        b['s8'] = P['circle_speed']
        b['s2'] = toward(b['s2'], P['circle_roll'], P['circle_rrate'])
    # $1d880: speed toward the demand, clamped by hull
    vmax = min(((a['hull'] & 0xffff) >> P['hull_shift']) + P['vmax_add'], P['vmax_cap'])
    s8 = b['s8']
    s8 = vmax if s8 > vmax else (P['vmin'] if s8 < P['vmin'] else s8)
    b['s8'] = s8
    if a['v'] != s8:
        b['v'] = toward(a['v'], s8, P['accel'] if a['v'] < s8 else P['decel'])
    # bit 7 / bit 6 stick decays (set only by manual flight)
    if b['flags'] & 0x80:
        if b['s2'] == 0: b['flags'] &= ~0x80
        else: b['s2'] = decay(b['s2'])
    if b['flags'] & 0x40:
        if b['s4'] == 0: b['flags'] &= ~0x40
        else: b['s4'] = decay(b['s4'])
    # $1d940: attitude from the stick
    b['roll'] = s16(b['s2'] * P['roll_k'])
    b['pitch'] = s16(b['s4'] * P['pitch_k'])
    b['heading'] = (a['heading'] + s16(trunc_div(s16(b['s2'] * P['yaw_mul']), P['yaw_div']))) & 0xffff
    # $1cf58, $19e2e: velocity from speed, pitch, heading
    v = b['v']
    if a['eflags'] & 2 and v > 200:
        v = 200
    vy, h = rot_fwd(0, v, b['pitch'])
    vx, vz = rot_inv(0, h, b['heading'])
    b['x'] = s32(a['x'] + vx)
    b['alt'] = min(s32(a['alt'] + vy), P['alt_cap'])
    b['z'] = s32(a['z'] + vz)
    return b


def read(s):
    sl = s.read(0x498, 52)
    e = s.read(0x5df5a, 24)
    h = lambda b, o: struct.unpack('>h', b[o:o + 2])[0]
    l = lambda b, o: struct.unpack('>l', b[o:o + 4])[0]
    return dict(flags=sl[0], state=sl[28], s2=h(sl, 2), s4=h(sl, 4), v=h(sl, 6), s8=h(sl, 8), fuel=h(sl, 10),
                hull=h(sl, 20), destx=l(sl, 30), talt=l(sl, 34), destz=l(sl, 38), cruise=h(sl, 42), c48=h(sl, 48),
                eflags=e[0], pitch=h(e, 4), heading=struct.unpack('>H', e[6:8])[0], roll=h(e, 8),
                x=l(e, 10), alt=l(e, 14), z=l(e, 18))


FIELDS = ['flags', 'state', 's2', 's4', 'v', 's8', 'c48', 'pitch', 'heading', 'roll', 'x', 'alt', 'z']


def main():
    snap, ticks = sys.argv[1], int(sys.argv[2])
    s = StServer(str(ROOT))
    s('load', snapshot=snap)
    s('poke', addr=0x126c, width=4, value=0x00ff0001)          # the crack's stack leak (README "Provenance")
    for p in sys.argv[3:]:
        addr, rest = p.split('=')
        val, width = rest.split(':')
        s('poke', addr=int(addr, 16), width=int(width), value=int(val, 16))
    s('bp_set', addrs=[0x1cab4])
    S = []
    for k in range(ticks + 1):
        r = s('run', max_steps=400000)
        assert r['reason'] == 'breakpoint', r
        S.append(read(s))
    s('bp_clear', addrs=[0x1cab4])
    s.close()
    assert S[0]['state'] == 3 and S[0]['flags'] & 1, S[0]
    n = len(S) - 1
    usable = [k for k in range(n) if S[k]['state'] == 3 and S[k]['alt'] >= 150 and S[k]['flags'] & 1]

    def score(verbose):
        ok = 0
        for k in usable:
            p, g = step(S[k]), S[k + 1]
            bad = [f for f in FIELDS if p[f] != g[f]]
            if bad and verbose:
                print(f'tick {k + 1}: ' + ', '.join(f'{f} model {p[f]} game {g[f]}' for f in bad))
            ok += not bad
        return ok
    ok = score(True)
    arr = [k for k in range(n) if S[k]['flags'] & 2 and not S[k + 1]['flags'] & 2]
    print(f'alt {S[0]["alt"]}..{max(x["alt"] for x in S)} (target {S[0]["talt"]}); heading '
          f'{S[0]["heading"]:#06x}..{S[-1]["heading"]:#06x}; speed {S[0]["v"]}..{S[-1]["v"]}; '
          f'destination cleared at tick {arr[0] + 1 if arr else None}; fuel {S[0]["fuel"]}..{S[-1]["fuel"]}')
    broke = 0
    for key, base in P0.items():
        P.clear(); P.update(P0)
        P[key] = base + (1 if base > 0 else -1)
        m = score(False)
        broke += m < len(usable)
        print(f'  control {key} = {P[key]}: {m}/{len(usable)}')
    P.clear(); P.update(P0)
    print(f'controls broken {broke}/{len(P0)}')
    print(f'flight ticks {len(usable)} match {ok}')


if __name__ == '__main__':
    main()
