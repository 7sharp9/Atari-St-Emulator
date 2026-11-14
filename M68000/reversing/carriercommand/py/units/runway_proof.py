#!/usr/bin/env python3
"""Prove the Manta's runway touchdown ($1ccb0..$1cdc8), the runway taxi (slot state +28 = 4, $1d4ac, phases 0-3) and
parking (+28 = 5, $1d5f8) against the emulator, on the airstrip of island 0 (VULCAN).

usage: runway_proof.py window
       runway_proof.py taxi <ticks> [u v alt heading speed]

From m_air.snap (Manta 0 airborne near the carrier, entity +60 = the block of island 0, whose record 1 is the airstrip
type $24) the Manta is poked onto an approach: position (u, v) in the runway's frame (the frame $1ccb0 computes:
position minus block minus the record's offset, rotated by minus the record's heading; every poked point is checked
to give exactly (u, v)), altitude, heading, speed and demand, sticks 0, autopilot with a destination 20,000 along
the runway at the same altitude. The crack fix (w 126c 00ff0001) comes first.

window: one tick from each of a set of approaches, in and just out of each limit of the touchdown test, reading
+28, hull and altitude after the first Manta update; prints one line per case and 'window cases N match M'. The
stick values poked are the ones that reach the test after that tick's autopilot step (roll stick toward about 0 by
32, pitch stick toward 0 by 10), so 152 is the roll limit 120 and 90 the pitch limit 80.

taxi: from the touchdown, slot 0 and its entity are read at every entry of $1cab4, and the model predicts each entry
in state 4 or 5 from the one before; prints mismatches, the phase timeline, 'taxi ticks N match M' and a control
per constant. Default approach (0, -3000), altitude 140, heading = the runway's, speed 60.
"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import struct
from atan_port import atan2
from flight_proof import s16, s32, rot_fwd, rot_inv, toward, decay

sys.path.insert(0, str(ROOT / 'tools'))
from stclient import StServer

SNAP = WORK / 'manta' / 'm_air.snap'
E, S = 0x5df5a, 0x498
m0 = ram(SNAP)
_l = lambda a: struct.unpack('>l', m0[a:a + 4])[0]
_h = lambda a: struct.unpack('>h', m0[a:a + 2])[0]
BLK = _l(E + 60)
BX, BZ = _l(BLK + 2), _l(BLK + 10)
REC = BLK + 82
assert _h(REC + 2) == 0x24, 'record 1 is not an airstrip'
RH, RX, RZ = _h(REC + 6) & 0xffff, _h(REC + 10), _h(REC + 14)


def frame(x, z):
    return rot_inv(s16(x - BX - RX), s16(z - BZ - RZ), -RH & 0xffff)


def world(u, v):
    ox, oz = rot_inv(u, v, RH)
    for ddx in range(-3, 4):
        for ddz in range(-3, 4):
            x, z = BX + RX + ox + ddx, BZ + RZ + oz + ddz
            if frame(x, z) == (u, v):
                return x, z
    raise SystemExit(f'no world point gives runway frame ({u}, {v})')


def start(u, v, alt, hd, sp, s2=0, s4=0):
    s = StServer(str(ROOT))
    s('load', snapshot=str(SNAP))
    P = lambda a, w, val: s('poke', addr=a, width=w, value=val & ((1 << 8 * w) - 1))
    P(0x126c, 4, 0x00ff0001)                                   # the crack's stack leak (README "Provenance")
    x, z = world(u, v)
    P(E + 10, 4, x); P(E + 18, 4, z); P(E + 14, 4, alt); P(E + 6, 2, hd); P(E + 4, 2, 0); P(E + 8, 2, 0)
    dx, dz = rot_inv(0, 20000, RH)
    P(S + 0, 1, 3); P(S + 28, 1, 3); P(S + 2, 2, s2); P(S + 4, 2, s4); P(S + 6, 2, sp); P(S + 8, 2, sp)
    P(S + 42, 2, sp); P(S + 30, 4, x + dx); P(S + 38, 4, z + dz); P(S + 34, 4, alt)
    s('bp_set', addrs=[0x1cab4])
    r = s('run', max_steps=400000)                             # this frame's Manta update, before it runs
    assert r['reason'] == 'breakpoint', r
    return s


def read(s):
    sl = s.read(S, 52)
    e = s.read(E, 24)
    h = lambda b, o: struct.unpack('>h', b[o:o + 2])[0]
    l = lambda b, o: struct.unpack('>l', b[o:o + 4])[0]
    return dict(flags=sl[0], state=sl[28], phase=sl[29], s2=h(sl, 2), s4=h(sl, 4), v=h(sl, 6), s8=h(sl, 8),
                fuel=h(sl, 10), hull=h(sl, 20), c48=h(sl, 48), w46=h(sl, 46),
                eflags=e[0], pitch=h(e, 4), heading=struct.unpack('>H', e[6:8])[0], roll=h(e, 8),
                x=l(e, 10), alt=l(e, 14), z=l(e, 18))


# ---- window ---------------------------------------------------------------------------------------------------

CASES = [  # (label, u, v, alt, heading offset, speed, s2, s4, expected outcome)
    ('centre', 0, -3000, 140, 0, 60, 0, 0, 'land'),
    ('across 200', 200, -3000, 140, 0, 60, 0, 0, 'land'), ('across 201', 201, -3000, 140, 0, 60, 0, 0, 'place'),
    ('across -200', -200, -3000, 140, 0, 60, 0, 0, 'land'), ('across -201', -201, -3000, 140, 0, 60, 0, 0, 'place'),
    ('along -4000', 0, -4000, 140, 0, 60, 0, 0, 'land'), ('along -4001', 0, -4001, 140, 0, 60, 0, 0, 'place'),
    ('along 2000', 0, 2000, 140, 0, 60, 0, 0, 'land'), ('along 2001', 0, 2001, 140, 0, 60, 0, 0, 'place'),
    ('roll 152', 0, -3000, 140, 0, 60, 152, 0, 'land'), ('roll 153', 0, -3000, 140, 0, 60, 153, 0, 'approach'),
    ('pitch 90', 0, -3000, 140, 0, 60, 0, 90, 'land'), ('pitch 91', 0, -3000, 140, 0, 60, 0, 91, 'approach'),
    ('heading +4000', 0, -3000, 140, 4000, 60, 0, 0, 'land'), ('heading +4001', 0, -3000, 140, 4001, 60, 0, 0, 'approach'),
    ('heading -4000', 0, -3000, 140, -4000, 60, 0, 0, 'land'), ('heading -4001', 0, -3000, 140, -4001, 60, 0, 0, 'approach'),
    ('speed 100', 0, -3000, 140, 0, 100, 0, 0, 'land'), ('speed 101', 0, -3000, 140, 0, 101, 0, 0, 'approach'),
    ('altitude 149', 0, -3000, 149, 0, 60, 0, 0, 'land'), ('altitude 150', 0, -3000, 150, 0, 60, 0, 0, 'fly'),
    ('altitude 36', 0, -3000, 36, 0, 60, 0, 0, 'land'), ('altitude 35', 0, -3000, 35, 0, 60, 0, 0, 'sea'),
]


def outcome(a, b):
    """What the first update did: land (+28 = 4), place (-500, the wrong place), approach (-100, a bad approach),
    sea (-2000, altitude 35 or less), fly (state 3, hull untouched)."""
    if b['state'] == 4:
        return 'land' if b['hull'] == a['hull'] else 'land?'
    loss = a['hull'] - b['hull']
    return {500: 'place', 100: 'approach', 2000: 'sea', 0: 'fly'}.get(loss, f'loss {loss}')


def window():
    ok = 0
    for lab, u, v, alt, dh, sp, s2, s4, want in CASES:
        s = start(u, v, alt, (RH + dh) & 0xffff, sp, s2, s4)
        a = read(s)
        r = s('run', max_steps=400000)
        assert r['reason'] == 'breakpoint', r
        b = read(s)
        s.close()
        got = outcome(a, b)
        floor = f', altitude {b["alt"]}' if got in ('place', 'approach') else ''
        print(f'{lab:14} {got:9} (want {want}){floor}')
        ok += got == want
    print(f'window cases {len(CASES)} match {ok}')


# ---- taxi and parking -----------------------------------------------------------------------------------------

P0 = dict(taxi_speed=64, taxi_alt=120, alt_rate=8, taxi_v=2650, near=150, bay_speed=8, bay_dx=600, bay_x0=900,
          bay_v0=3270, bay_v1=3720, bay_near=20, head_rate=0x200, turn_rate=0x400, park_alt=100, park_pitch=-694,
          refuel=64, hull_shift=4, vmax_add=50, vmax_cap=250, accel=4, decel=16, clr_bug=1)
P = dict(P0)


def speed(b):
    """$1d880 in states 4 to 6: the demand clamped to [0, min(hull / 16 + 50, 250)], speed toward it."""
    vmax = min(((b['hull'] & 0xffff) >> P['hull_shift']) + P['vmax_add'], P['vmax_cap'])
    s8 = b['s8']
    s8 = vmax if s8 > vmax else (0 if s8 < 0 else s8)
    b['s8'] = s8
    if b['v'] != s8:
        b['v'] = toward(b['v'], s8, P['accel'] if b['v'] < s8 else P['decel'])


def integrate(b):
    """$1cf58: velocity from speed, the entity's pitch and heading."""
    v = b['v']
    if b['eflags'] & 2 and v > 200:
        v = 200
    vy, h = rot_fwd(0, v, b['pitch'])
    vx, vz = rot_inv(0, h, b['heading'])
    b['x'] = s32(b['x'] + vx)
    b['alt'] = min(s32(b['alt'] + vy), 3500)
    b['z'] = s32(b['z'] + vz)


def to_point(b, u, v):
    """$1d7d4: the runway-frame point (u, v) in the world, minus the Manta's position."""
    ox, oz = rot_inv(u, v, RH)
    tx, tz = BX + s16(RX + ox), BZ + s16(RZ + oz)
    return s32(tx - b['x']), s32(tz - b['z'])


def head_for(b, dx, dz):
    """$1d812: heading toward the point by $200, speed, integrate."""
    b['heading'] = toward(b['heading'], atan2(dx, dz), P['head_rate']) & 0xffff
    speed(b)
    integrate(b)


def step(a):
    b = dict(a)
    if b['c48']:
        b['c48'] -= 1
    if a['state'] == 5:                                        # $1d5f8: parked, refuelling
        f = s16(b['fuel'] + P['refuel'])
        b['fuel'] = 0x7fff if f < 0 else f
        return b
    ph = a['phase']
    if ph == 0:                                                # $1d4dc: taxi to (0, 2650), settle to 120
        b['s8'] = P['taxi_speed']
        b['s4'] = decay(b['s4']); b['s2'] = decay(b['s2']); b['roll'] = decay(b['roll']); b['pitch'] = decay(b['pitch'])
        b['alt'] = toward(s16(a['alt']), P['taxi_alt'], P['alt_rate'])
        dx, dz = to_point(b, 0, P['taxi_v'])
        if abs(s16(dx)) <= P['near'] and abs(s16(dz)) <= P['near']:
            b['phase'] = 1
            b['alt'] = P['taxi_alt']
            b['s2'] = b['s4'] = b['pitch'] = b['roll'] = 0
            if P['clr_bug']:                                   # $1d53e clr.w D0 also clears the steer's dx low word
                dx = s32(dx & ~0xffff)
        head_for(b, dx, dz)
    elif ph == 1:                                              # $1d554: roll to the bay at speed 8
        b['s8'] = P['bay_speed']
        i = 0                                                  # entity +26: Manta 0
        u = s16(i * P['bay_dx'] - P['bay_x0'])
        v = P['bay_v0'] if i in (0, 3) else P['bay_v1']
        dx, dz = to_point(b, u, v)
        if abs(s16(dx)) <= P['bay_near'] and abs(s16(dz)) <= P['bay_near']:
            b['phase'] = 2
            b['s8'] = 0
            b['v'] = 0
        head_for(b, dx, dz)
    elif ph == 2:                                              # $1d5a4: turn to face down the runway
        b['s2'] = decay(b['s2'])
        tgt = (RH + 0x8000) & 0xffff
        if a['heading'] == tgt:
            b['phase'] = 3
        b['heading'] = toward(a['heading'], tgt, P['turn_rate']) & 0xffff
        integrate(b)
    elif ph == 3:                                              # $1d5d2: settle to 100, parked
        alt = s32(a['alt'] - 1)
        if alt <= P['park_alt']:
            alt = P['park_alt']
            b['pitch'] = P['park_pitch']
            b['state'] = 5
        b['alt'] = alt
    return b


FIELDS = ['flags', 'state', 'phase', 's2', 's4', 'v', 's8', 'fuel', 'hull', 'c48', 'pitch', 'heading', 'roll', 'x',
          'alt', 'z']


def taxi(ticks, u=0, v=-3000, alt=140, dh=0, sp=60):
    s = start(u, v, alt, (RH + dh) & 0xffff, sp)
    S_ = [read(s)]
    for k in range(ticks):
        r = s('run', max_steps=400000)
        assert r['reason'] == 'breakpoint', r
        S_.append(read(s))
    s('bp_clear', addrs=[0x1cab4])
    s.close()
    assert S_[1]['state'] == 4, ('no touchdown', S_[1])
    n = len(S_) - 1
    usable = [k for k in range(1, n) if S_[k]['state'] in (4, 5) and S_[k]['w46'] != 2]

    def score(verbose):
        ok = 0
        for k in usable:
            p, g = step(S_[k]), S_[k + 1]
            bad = [f for f in FIELDS if p[f] != g[f]]
            if bad and verbose:
                print(f'tick {k + 1} (state {S_[k]["state"]} phase {S_[k]["phase"]}): '
                      + ', '.join(f'{f} model {p[f]} game {g[f]}' for f in bad))
            ok += not bad
        return ok
    ok = score(True)
    tl, last = [], None
    for k, x in enumerate(S_):
        if (x['state'], x['phase']) != last:
            last = (x['state'], x['phase'])
            tl.append(f'{x["state"]}.{x["phase"]}@{k}')
    print('timeline (state.phase@tick): ' + ' '.join(tl))
    f = S_[-1]
    print(f'parked at runway frame {frame(f["x"], f["z"])}, heading {f["heading"]:#06x} (runway {RH:#06x}), '
          f'altitude {f["alt"]}, fuel {S_[1]["fuel"]}..{f["fuel"]}')
    broke = 0
    for key, base in P0.items():
        P.clear(); P.update(P0)
        P[key] = 0 if key == 'clr_bug' else base + (1 if base > 0 else -1)
        m = score(False)
        broke += m < len(usable)
        print(f'  control {key} = {P[key]}: {m}/{len(usable)}')
    P.clear(); P.update(P0)
    print(f'controls broken {broke}/{len(P0)}')
    print(f'taxi ticks {len(usable)} match {ok}')


if __name__ == '__main__':
    if sys.argv[1] == 'window':
        window()
    else:
        taxi(int(sys.argv[2]), *map(int, sys.argv[3:]))
