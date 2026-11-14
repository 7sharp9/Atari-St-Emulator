#!/usr/bin/env python3
"""Prove the Walrus autopilot ($1da24: launch state 2, cruise state 3, docking state 0) and the shared motion code
($1dc80) against the emulator, tick by tick.

usage: walrus_proof.py <ticks> [--dock <tick>] [addr=value:width ...]

From c_s30.snap (Walrus 0 in its hangar, selected: $de0 = 0, $56a/$56e its slot and entity) the pokes are applied
after the crack fix (w 126c 00ff0001); then the game's launch command $1201a is called. With --dock <tick>, the dock
command $122d6 is called at that tick (the Walrus must be inside its cone behind the carrier). At every entry of the
Walrus update $1da24 (one per main frame) slot 0 ($572, 52 bytes) and its entity ($5e45a) are read with $122d, $de2,
the dock door $dd4, the carrier ($5e95a entity: heading +6, x +10, z +18; speed $646) and the 16th-frame flag $8fb;
the model predicts each entry from the one before (the carrier, the door and $8fb are inputs read at the earlier
entry). Prints mismatches, the timeline, 'walrus ticks N match M', then a control per constant.
"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import struct
from atan_port import atan2
from flight_proof import s16, s32, trunc_div, rot_inv, toward, decay

sys.path.insert(0, str(ROOT / 'tools'))
from stclient import StServer

S, E = 0x572, 0x5e45a
P0 = dict(back_accel=8, back_vmax=60, back_end=1500, aim=0x400, rud_shift=5, rud_max=255, rud_rate=32, near=1000,
          near_cap=32, arrive=250, yaw_mul=16, yaw_div=6, hull_shift=5, cap=96, sea_cap=48, accel=2, decel=8,
          fuel_shift=4, fuel_div=80, fuel_low=128, buoy_k=0x1111, buoy_off=0x200, waterline=15,
          dock_back=1500, dock_range=0x4000, dock_speed=60, dock_near_speed=24, dock_reach=200, dock_turn=0x200,
          dock_slide=32, dock_end=650)
P = dict(P0)


def from_deck(b, a):
    """$1e0ec: the deck offset (entity +28/+30) rotated by the carrier heading plus the carrier position."""
    x, z = rot_inv(b['d28'], b['d30'], a['ch'])
    b['x'], b['z'] = s32(a['cx'] + x), s32(a['cz'] + z)


def rudder_to(b, err):
    t = max(-P['rud_max'], min(P['rud_max'], err >> P['rud_shift']))
    b['rud'] = toward(b['rud'], t, P['rud_rate'])


def motion(b, a):
    """$1dc80: the shared code for every Walrus not in a scripted dock phase."""
    # the coast band test ($1dc80..$1dcb2) is asserted away: these runs stay in open sea
    b['flags'] &= ~0x08
    w = s16(b['alt'] - P['waterline'])
    b['e36'] = P['buoy_off'] if w >= 0 else s16(((w * P['buoy_k']) >> 8) + P['buoy_off'])
    if a['f8fb']:                                              # fuel, every 16th frame
        d0 = ((max(b['v'], 0) << P['fuel_shift']) & 0xffff) // P['fuel_div']
        if b['hull'] <= 500:
            d0 += P['fuel_low']
        if b['fuel']:
            b['fuel'] = b['fuel'] - d0 if (b['fuel'] & 0xffff) > d0 else 0
    # $1e3ce: the demand clamped by fuel, hull and the water, then the speed toward it
    if b['fuel'] == 0:
        d0 = 0
        b['dem'] = 0
    else:
        cap = min((b['hull'] & 0xffff) >> P['hull_shift'], P['cap'])
        if b['alt'] < 0:
            cap = min(cap, P['sea_cap'])
        d0 = max(0, min(b['dem'], cap))
        b['dem'] = d0
    if b['v'] != d0:
        b['v'] = toward(b['v'], d0, P['accel'] if b['v'] < d0 else P['decel'])
    if b['flags'] & 0x80:
        if b['rud'] == 0: b['flags'] &= ~0x80
        else: b['rud'] = decay(b['rud'])
    if b['flags'] & 0x40:
        if b['e38'] == 0: b['flags'] &= ~0x40
        else: b['e38'] = toward(b['e38'], 0, 0x400)
    turn = s16(trunc_div(s16(b['rud'] * P['yaw_mul']), P['yaw_div']))
    if b['flags'] & 0x20:
        b['e38'] = s16(b['e38'] + turn)
    else:
        b['heading'] = (b['heading'] + turn) & 0xffff
    vx, vz = rot_inv(0, b['v'], b['heading'])
    b['x'], b['z'] = s32(b['x'] + vx), s32(b['z'] + vz)


def err_to(b, tx, tz):
    dx, dz = s32(tx - b['x']), s32(tz - b['z'])
    return s16(atan2(dx, dz) - b['heading']), max(abs(dx), abs(dz))


def step(a):
    b = dict(a)
    if b['c48']:
        b['c48'] -= 1
    b['w44'] = 0
    if not a['flags'] & 1:                                     # autopilot off, not the viewed craft
        motion(b, a)
        return b
    st, ph = a['st'], a['ph']
    if st == 2 and ph == 0:                                    # $1dffe: back out of the stern dock
        v = (b['v'] + P['back_accel']) & 0xffff
        b['v'] = P['back_vmax'] if v > P['back_vmax'] else v
        b['d30'] = s16(b['d30'] - b['v'])
        if b['d30'] <= -P['back_end']:
            b['ph'] = 1
        b['heading'] = (a['ch'] + 0x8000) & 0xffff
        from_deck(b, a)
    elif st == 2 and ph == 1:                                  # $1e04a: pivot behind the stern to the destination
        err, _ = err_to(b, a['destx'], a['destz'])
        if abs(err) <= P['aim']:
            b['ph'] = 2
        rudder_to(b, err)
        b['dem'] = 0
        from_deck(b, a)
        motion(b, a)
    elif st == 2 and ph == 2:                                  # $1e0a8: away, with the carrier's speed
        b['v'] = s16(b['v'] + a['cv'])
        b['dem'] = b['v']
        b['e1'] &= ~4
        b['st'], b['ph'] = 3, 0
        b['de2'] = s16(0xff00 | (b['de2'] & 0xff))         # st $de2.w: the high byte only
        b['b122d'] = 0
        if b['b51']:
            b['flags'] &= ~1
    elif st == 3:                                              # $1e124: to the destination
        if b['flags'] & 2:
            err, d = err_to(b, a['destx'], a['destz'])
            d4 = b['cruise']
            if d <= P['near'] and d4 > P['near_cap']:
                d4 = P['near_cap']
            b['dem'] = d4
            if d >= P['arrive']:
                if abs(err) > P['aim']:
                    b['dem'] = 0
                rudder_to(b, err)
                motion(b, a)
                return b
            b['flags'] &= 0xfc                                  # arrived: autopilot and destination off
        b['flags'] |= 0x80
        b['dem'] = 0
        motion(b, a)
    elif st == 0 and ph == 0:                                  # $1ddea: to 1500 behind the stern
        ox, oz = rot_inv(0, -P['dock_back'], a['ch'])
        err, d = err_to(b, s32(a['cx'] + ox), s32(a['cz'] + oz))
        if d > P['dock_range']:
            raise ValueError('out of docking range (not modelled)')
        d4 = P['dock_speed']
        if d <= P['near'] and d4 > P['dock_near_speed']:
            d4 = P['dock_near_speed']
        b['dem'] = d4
        if d >= P['dock_reach']:
            if abs(err) > P['aim']:
                b['dem'] = 0
            rudder_to(b, err)
            motion(b, a)
        else:
            b['d28'], b['d30'] = rot_inv(s16(a['x'] - a['cx']), s16(a['z'] - a['cz']), -a['ch'] & 0xffff)
            b['ph'] = 1
            b['de2'] = 0                                       # Walrus 0
            b['e1'] |= 4                                       # $1d994: the craft named by $de2 marked (bit 2)
    elif st == 0 and ph == 1:                                  # $1df1c: turn to the carrier's heading
        b['heading'] = toward(a['heading'], a['ch'], P['dock_turn']) & 0xffff
        from_deck(b, a)
        if b['heading'] == a['ch']:
            b['ph'] = 2
    elif st == 0 and ph == 2:                                  # $1df52: slide into the dock
        b['d30'] = s16(b['d30'] + P['dock_slide'])
        if b['d30'] >= -P['dock_end']:
            b['ph'] = 3
        from_deck(b, a)
    elif st == 0 and ph == 3:                                  # $1df74: wait for the door, then stow
        if a['dd4'] != 0xd000:
            from_deck(b, a)
        else:
            b['e1'] &= ~1
            b['b122d'] = 0
            b['w12'] = 0
            b['u1'] = 0
            b['w38'] = b['w40'] = b['w18'] = 0
            b['de2'] = s16(0xff00 | (b['de2'] & 0xff))         # st $de2.w: the high byte only
    else:
        raise ValueError((st, ph))
    return b


def read(s):
    sl = s.read(S, 52)
    e = s.read(E, 40)
    c = s.read(0x5e95a, 24)
    h = lambda b, o: struct.unpack('>h', b[o:o + 2])[0]
    l = lambda b, o: struct.unpack('>l', b[o:o + 4])[0]
    return dict(flags=sl[0], u1=sl[1], rud=h(sl, 2), v=h(sl, 4), dem=h(sl, 6), fuel=h(sl, 8), w12=h(sl, 12),
                w18=h(sl, 18), hull=h(sl, 20), st=sl[26], ph=sl[27], destx=l(sl, 28), destz=l(sl, 32),
                cruise=h(sl, 36), w38=h(sl, 38), w40=h(sl, 40), w44=h(sl, 44), c48=h(sl, 48), b51=sl[51],
                e1=e[1], heading=struct.unpack('>H', e[6:8])[0], x=l(e, 10), alt=l(e, 14), z=l(e, 18),
                d28=h(e, 28), d30=h(e, 30), e36=h(e, 36), e38=h(e, 38),
                b122d=s.read(0x122d, 1)[0], de2=struct.unpack('>h', s.read(0xde2, 2))[0],
                dd4=struct.unpack('>H', s.read(0xdd4, 2))[0], f8fb=s.read(0x8fb, 1)[0],
                ch=struct.unpack('>H', c[6:8])[0], cx=l(c, 10), cz=l(c, 18), cv=struct.unpack('>h', s.read(0x646, 2))[0])


FIELDS = ['flags', 'u1', 'rud', 'v', 'dem', 'fuel', 'w12', 'w18', 'hull', 'st', 'ph', 'destx', 'destz', 'cruise',
          'w38', 'w40', 'w44', 'c48', 'b51', 'e1', 'heading', 'x', 'alt', 'z', 'd28', 'd30', 'e36', 'e38', 'b122d',
          'de2']


def main():
    args = sys.argv[1:]
    ticks = int(args.pop(0))
    dock = None
    if args and args[0] == '--dock':
        args.pop(0)
        dock = int(args.pop(0))
    s = StServer(str(ROOT))
    s('load', snapshot=str(ANCHOR))
    s('poke', addr=0x126c, width=4, value=0x00ff0001)          # the crack's stack leak (README "Provenance")
    for p in args:
        addr, rest = p.split('=')
        val, width = rest.split(':')
        s('poke', addr=int(addr, 16), width=int(width), value=int(val, 16))
    assert struct.unpack('>l', s.read(0x9fa, 4))[0] != E, 'Walrus 0 is the viewed craft'
    s.call_resume(0x1201a, d2=2)                                # launch
    s('bp_set', addrs=[0x1da24])
    T, skip = [], set()
    for k in range(ticks + 1):
        if dock is not None and k == dock:
            s('bp_clear', addrs=[0x1da24])
            s.call_resume(0x122d6, d2=2)                        # dock
            s('bp_set', addrs=[0x1da24])
            skip.add(k - 1)                                     # the call changed the state after this read
        r = s('run', max_steps=400000)
        assert r['reason'] == 'breakpoint', r
        T.append(read(s))
        if T[-1]['u1'] < 3:
            break
    s('bp_clear', addrs=[0x1da24])
    s.close()
    n = len(T) - 1
    usable = [k for k in range(n) if k not in skip and T[k]['u1'] >= 3 and T[k]['e1'] & 1]

    def score(verbose):
        ok = 0
        for k in usable:
            try:
                p = step(T[k])
            except ValueError as ex:
                if verbose:
                    print(f'tick {k + 1}: {ex}')
                continue
            g = T[k + 1]
            bad = [f for f in FIELDS if p[f] != g[f]]
            if bad and verbose:
                print(f'tick {k + 1} (state {T[k]["st"]} phase {T[k]["ph"]} flags {T[k]["flags"]:#04x}): '
                      + ', '.join(f'{f} model {p[f]} game {g[f]}' for f in bad))
            ok += not bad
        return ok
    ok = score(True)
    tl, last = [], None
    for k, x in enumerate(T):
        if k - 1 in skip:
            tl.append(f'dock@{k}')
        key = (x['st'], x['ph'], x['flags'] & 1, x['u1'])
        if key != last:
            last = key
            tl.append(f'{x["st"]}.{x["ph"]}{"" if x["flags"] & 1 else "m"}{"" if x["u1"] >= 3 else " stowed"}@{k}')
    print('timeline (state.phase, m = autopilot off): ' + ' '.join(tl))
    f = T[-1]
    print(f'speed max {max(x["v"] for x in T)}, fuel {T[0]["fuel"]}..{f["fuel"]}, carrier heading '
          f'{T[0]["ch"]:#06x}..{f["ch"]:#06x} speed {T[0]["cv"]}..{f["cv"]}')
    broke = 0
    for key, base in P0.items():
        P.clear(); P.update(P0)
        P[key] = base + (1 if base > 0 else -1)
        m = score(False)
        broke += m < ok
        print(f'  control {key} = {P[key]}: {m}/{len(usable)}')
    P.clear(); P.update(P0)
    print(f'controls broken {broke}/{len(P0)}')
    print(f'walrus ticks {len(usable)} match {ok}')


if __name__ == '__main__':
    main()
