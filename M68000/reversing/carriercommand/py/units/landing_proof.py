#!/usr/bin/env python3
"""Prove the Manta deck landing (slot state +28 = 0 under autopilot, $1cfc2, phases +29 = 0..4) and the hand-off to
the deck (+28 = 1, $1d200) against the emulator, tick by tick.

usage: landing_proof.py [--stow] <snap> <ticks> [addr=value:width ...]

<snap> is m_air.snap (Manta 0 airborne and circling near the carrier; py/units/manta_snaps.py rebuilds it). The
pokes are applied after the crack fix (w 126c 00ff0001); 644=00400000:4 648=00300000:4 set the carrier turning and
moving, as in takeoff_proof.py. Then the game's own land command $11bf6 is called (the selected Manta is $490/$494,
slot 0 in the snapshot), and at every entry of the Manta update $1cab4 (one per main frame) slot 0 ($498), its entity
($5df5a), $dcc, $122c, the carrier ($5e95a entity: heading +6, x +10, z +18; speed $646) and the 16th-frame flag $8fb
are read. The model predicts each entry from the one before; the carrier and $8fb are inputs read at the earlier
entry, because the carrier update and the $8fb counter run before the Manta update in the same frame.
Prints one line per mismatching field, the phase timeline, 'landing ticks N match M', then a control per constant.
With --stow, once the run ends with the Manta on deck (+28 = 1), the game's lift-down command $11f3c is called and the
run continues until the lift is at rest again ($dca = 0): it prints the ticks to the bottom (+28 = 0, +1 = 0, $dcc
empty) and to the lift at rest, with the altitude per tick (the lift's own motion is recorded, not modelled).
"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import struct
from atan_port import atan2
from flight_proof import s16, s32, trunc_div, sc, rot_fwd, rot_inv, toward, decay

sys.path.insert(0, str(ROOT / 'tools'))
from stclient import StServer

P0 = dict(alt_target=570, alt_dead=20, pitch_tgt=100, pitch_rate=20, arrive=600, far=3500, far_speed=200,
          near_speed=65, div_far=10, div_near=32, turn_rate=32, stick_max=255,
          hull_shift=4, vmin=50, vmax_add=50, vmax_cap=250, accel=4, decel=16, roll_k=-25, pitch_k=-14, yaw_mul=16,
          yaw_div=6, alt_cap=3500, fuel_shift=4, fuel_div=50,
          deck_z=250, slide=10, head_rate=0x200, descend=10, deck_alt=180, deck_pitch=-694, deck_fuel=12)
P = dict(P0)


def speed(b):
    """$1d880: clamp the demand +8 to [vmin, min(hull / 16 + 50, 250)] and move the speed +6 toward it."""
    vmax = min(((b['hull'] & 0xffff) >> P['hull_shift']) + P['vmax_add'], P['vmax_cap'])
    s8 = b['s8']
    s8 = vmax if s8 > vmax else (P['vmin'] if s8 < P['vmin'] else s8)
    b['s8'] = s8
    if b['v'] != s8:
        b['v'] = toward(b['v'], s8, P['accel'] if b['v'] < s8 else P['decel'])


def deck_to_world(b, a):
    """$1d908: the deck offset (entity +28/+30) rotated by the carrier heading ($a0a4) plus the carrier position."""
    x, z = rot_inv(b['d28'], b['d30'], a['ch'])
    b['x'], b['z'] = s32(a['cx'] + x), s32(a['cz'] + z)


def steer(b, a, dx, dz, div):
    """$1d41c/$1d420: roll stick toward the heading error to the carrier over div, by 32."""
    t = s16(atan2(dx, dz) - b['heading'])
    t = s16(trunc_div(t, div))
    t = max(-P['stick_max'], min(P['stick_max'], t))
    b['s2'] = toward(b['s2'], t, P['turn_rate'])


def fly(b, a):
    """$1ccb0 at altitude >= 150 under autopilot in state 0: fuel ($1ce56), speed again ($1cf14), stick decays,
    attitude ($1d940), integration ($1cf58)."""
    if a['f8fb']:
        b['fuel'] = max(0, s16(b['fuel'] - ((b['v'] & 0xffff) << P['fuel_shift'] & 0xffff) // P['fuel_div']
                               - (256 if b['hull'] <= 500 else 0)))
    speed(b)
    if b['flags'] & 0x80:
        if b['s2'] == 0: b['flags'] &= ~0x80
        else: b['s2'] = decay(b['s2'])
    if b['flags'] & 0x40:
        if b['s4'] == 0: b['flags'] &= ~0x40
        else: b['s4'] = decay(b['s4'])
    b['roll'] = s16(b['s2'] * P['roll_k'])
    b['pitch'] = s16(b['s4'] * P['pitch_k'])
    b['heading'] = (b['heading'] + s16(trunc_div(s16(b['s2'] * P['yaw_mul']), P['yaw_div']))) & 0xffff
    v = b['v']
    if a['eflags'] & 2 and v > 200:
        v = 200
    vy, h = rot_fwd(0, v, b['pitch'])
    vx, vz = rot_inv(0, h, b['heading'])
    b['x'] = s32(b['x'] + vx)
    b['alt'] = min(s32(b['alt'] + vy), P['alt_cap'])
    b['z'] = s32(b['z'] + vz)


def deck(b, a):
    """$1d200, state 1 (also the tail of phase 4): fuel -12 on 16th frames, heading and position from the deck."""
    if a['f8fb']:
        b['fuel'] = max(0, s16(b['fuel'] - P['deck_fuel']))
    b['heading'] = a['ch']
    deck_to_world(b, a)


def step(a):
    """The state at the next $1cab4 entry from the state at this one (Manta 0, autopilot, +28 = 0 or 1)."""
    b = dict(a)
    if b['c48']:
        b['c48'] -= 1
    if a['state'] == 1:
        deck(b, a)
        return b
    # $1cfc2: every phase
    b['pitch'] = decay(b['pitch'])
    b['roll'] = decay(b['roll'])
    speed(b)
    b['s4'] = decay(b['s4'])
    b['s2'] = decay(b['s2'])
    ph = a['phase']
    if ph == 0:
        dalt = s32(P['alt_target'] - a['alt'])
        tgt = 0
        if abs(dalt) >= P['alt_dead']:
            tgt = P['pitch_tgt'] if s16(dalt) >= 0 else -P['pitch_tgt']
        b['s4'] = toward(b['s4'], tgt, P['pitch_rate'])
        dx, dz = s32(a['cx'] - a['x']), s32(a['cz'] - a['z'])
        d = max(abs(dx), abs(dz))
        if d >= P['arrive']:
            b['s8'] = P['far_speed'] if d - P['arrive'] >= P['far'] else P['near_speed']
            steer(b, a, dx, dz, P['div_far'])
            fly(b, a)
            return b
        if b['s4'] != 0:
            steer(b, a, dx, dz, P['div_near'])
            fly(b, a)
            return b
        # $1d076: on station; deck offset in the world frame, velocity relative to the carrier's
        b['d28'], b['d30'] = s16(-dx), s16(-dz)
        cvx, cvz = rot_inv(0, a['cv'], a['ch'])
        mvx, mvz = rot_inv(0, b['v'], b['heading'])
        b['r32'], b['r36'] = s16(mvx - cvx), s16(mvz - cvz)
        b['phase'] = ph = 1
        b['s8'] = 0
    if ph == 1:                                 # $1d0d8: relative velocity decays, Manta carried with the carrier
        b['r32'] = decay(b['r32'])
        b['d28'] = s16(b['d28'] + b['r32'])
        b['r36'] = decay(b['r36'])
        b['d30'] = s16(b['d30'] + b['r36'])
        b['x'], b['z'] = s32(a['cx'] + b['d28']), s32(a['cz'] + b['d30'])
        if s16(b['r32'] + b['r36']) == 0:       # offset into the carrier's frame
            b['phase'] = 2
            b['d28'], b['d30'] = rot_inv(b['d28'], b['d30'], -a['ch'] & 0xffff)
        return b
    if ph == 2:                                 # $1d138: turn to the carrier's heading
        b['heading'] = toward(b['heading'], a['ch'], P['head_rate']) & 0xffff
        deck_to_world(b, a)
        if b['heading'] == a['ch']:
            b['phase'] = 3
        return b
    if ph == 3:                                 # $1d16e: slide to the deck spot
        if b['d30'] == P['deck_z'] and b['d28'] == 0:
            b['dcc'] = 0                         # entity +26, Manta 0
            b['phase'] = 4
            return b
        b['d30'] = toward(b['d30'], P['deck_z'], P['slide'])
        b['d28'] = toward(b['d28'], 0, P['slide'])
        b['heading'] = a['ch']
        deck_to_world(b, a)
        return b
    if ph == 4:                                 # $1d1c6: descend to the deck
        alt = s32(a['alt'] - P['descend'])
        if alt <= P['deck_alt']:
            alt = P['deck_alt']
            b['pitch'] = P['deck_pitch']
            b['phase'] = 0
            b['state'] = 1
            b['b122c'] = 0
        b['alt'] = alt
        deck(b, a)
        return b
    raise ValueError(ph)


def read(s):
    sl = s.read(0x498, 52)
    e = s.read(0x5df5a, 40)
    c = s.read(0x5e95a, 24)
    h = lambda b, o: struct.unpack('>h', b[o:o + 2])[0]
    l = lambda b, o: struct.unpack('>l', b[o:o + 4])[0]
    return dict(flags=sl[0], state=sl[28], phase=sl[29], s2=h(sl, 2), s4=h(sl, 4), v=h(sl, 6), s8=h(sl, 8),
                fuel=h(sl, 10), hull=h(sl, 20), c48=h(sl, 48),
                eflags=e[0], pitch=h(e, 4), heading=struct.unpack('>H', e[6:8])[0], roll=h(e, 8),
                x=l(e, 10), alt=l(e, 14), z=l(e, 18), d28=h(e, 28), d30=h(e, 30), r32=h(e, 32), r36=h(e, 36),
                dcc=struct.unpack('>h', s.read(0xdcc, 2))[0], b122c=s.read(0x122c, 1)[0],
                ch=struct.unpack('>H', c[6:8])[0], cx=l(c, 10), cz=l(c, 18),
                cv=struct.unpack('>h', s.read(0x646, 2))[0], f8fb=s.read(0x8fb, 1)[0])


FIELDS = ['flags', 'state', 'phase', 's2', 's4', 'v', 's8', 'fuel', 'c48', 'pitch', 'heading', 'roll', 'x', 'alt', 'z',
          'd28', 'd30', 'r32', 'r36', 'dcc', 'b122c']


def main():
    stow = '--stow' in sys.argv
    if stow:
        sys.argv.remove('--stow')
    snap, ticks = sys.argv[1], int(sys.argv[2])
    s = StServer(str(ROOT))
    s('load', snapshot=snap)
    s('poke', addr=0x126c, width=4, value=0x00ff0001)          # the crack's stack leak (README "Provenance")
    for p in sys.argv[3:]:
        addr, rest = p.split('=')
        val, width = rest.split(':')
        s('poke', addr=int(addr, 16), width=int(width), value=int(val, 16))
    s.call_resume(0x11bf6)                                      # land
    s('bp_set', addrs=[0x1cab4])
    S = []
    for k in range(ticks + 1):
        r = s('run', max_steps=400000)
        assert r['reason'] == 'breakpoint', r
        S.append(read(s))
    stowed = None
    if stow and S[-1]['state'] == 1:
        s('bp_clear', addrs=[0x1cab4])
        s.call_resume(0x11f3c)                                  # lift down
        s('bp_set', addrs=[0x1cab4])
        alts, bottom = [], None
        for k in range(100):
            r = s('run', max_steps=400000)
            assert r['reason'] == 'breakpoint', r
            x = read(s)
            u1 = s.read(0x499, 1)[0]
            alts.append(x['alt'])
            if bottom is None and x['state'] == 0 and u1 == 0 and x['dcc'] < 0:
                bottom = k + 1
            if bottom is not None and struct.unpack('>h', s.read(0xdca, 2))[0] == 0:
                stowed = (bottom, k + 1, alts)
                break
    s('bp_clear', addrs=[0x1cab4])
    s.close()
    assert S[0]['state'] == 0 and S[0]['phase'] == 0 and S[0]['flags'] & 1, S[0]
    n = len(S) - 1
    usable = [k for k in range(n) if S[k]['state'] in (0, 1) and S[k]['flags'] & 1 and S[k]['alt'] >= 150]

    def score(verbose):
        ok = 0
        for k in usable:
            p, g = step(S[k]), S[k + 1]
            bad = [f for f in FIELDS if p[f] != g[f]]
            if bad and verbose:
                print(f'tick {k + 1} (state {S[k]["state"]} phase {S[k]["phase"]}): '
                      + ', '.join(f'{f} model {p[f]} game {g[f]}' for f in bad))
            ok += not bad
        return ok
    ok = score(True)
    tl, last = [], None
    for k, x in enumerate(S):
        if (x['state'], x['phase']) != last:
            last = (x['state'], x['phase'])
            tl.append(f'{x["state"]}.{x["phase"]}@{k}')
    print('timeline (state.phase@tick): ' + ' '.join(tl))
    print(f'carrier heading {S[0]["ch"]:#06x}..{S[-1]["ch"]:#06x} speed {S[0]["cv"]}..{S[-1]["cv"]}; '
          f'Manta alt {S[0]["alt"]}..{S[-1]["alt"]} speed {S[0]["v"]}..{S[-1]["v"]} fuel {S[0]["fuel"]}..{S[-1]["fuel"]}; '
          f'deck offset ({S[-1]["d28"]}, {S[-1]["d30"]})')
    broke = 0
    for key, base in P0.items():
        P.clear(); P.update(P0)
        P[key] = base + (1 if base > 0 else -1)
        m = score(False)
        broke += m < len(usable)
        print(f'  control {key} = {P[key]}: {m}/{len(usable)}')
    P.clear(); P.update(P0)
    print(f'controls broken {broke}/{len(P0)}')
    print(f'landing ticks {len(usable)} match {ok}')
    if stow:
        if stowed:
            print(f'stow: hangar (+28 = 0, +1 = 0, deck empty) after {stowed[0]} ticks, lift at rest after {stowed[1]}; '
                  f'altitude {" ".join(map(str, stowed[2][:stowed[0]]))}')
        else:
            print('stow: not reached')


if __name__ == '__main__':
    main()
