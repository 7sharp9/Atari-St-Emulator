"""Exact integer model of Virus's ship tick from $255d4 (free flight), lifted from reversing/virus/py/virus_flight.py
and extended from the listing in tick.asm with: the fuel test on thrust ($25688..$2569c), the fire cost ($2572a),
and the ground/altitude test after the position update ($257ee..$2587c) as a classifier of the path the game takes.

    import exact
    pos, vel, att = exact.step(pos, vel, att, d0, d1, d2, g)                 # fuel assumed sufficient
    r = exact.step_full(pos, vel, att, d0, d1, d2, g, fuel)                 # dict: pos vel att fuel thrust ceiling
    exact.ground(x, z)     -> D1 as $245b8 returns it (landscape 0 only)
    exact.classify(pos_after, vy_before_gravity, objmap=None) -> 'free' | 'low' | 'ground'

All values signed 16-bit in, signed 16-bit out. y grows downward (gravity adds to vy; thrust subtracts).
att[0] (target D0) is the tilt from vertical, att[1] (target D1) the heading; $10000 is a full turn.
The sine table is read from the snapshot ($d0fa, 1024 words), default scratchpad/virus/fl/f1.snap.
"""
import os
import struct
import sys

_d = os.path.dirname(os.path.abspath(__file__))
ROOT = _d
while not os.path.exists(os.path.join(ROOT, 'tools', 'rdis.py')):
    p = os.path.dirname(ROOT)
    if p == ROOT:
        raise SystemExit('repo root (the directory holding tools/rdis.py) not found')
    ROOT = p
DEFAULT_SNAP = os.path.join(ROOT, 'scratchpad', 'virus', 'fl', 'f1.snap')

_S = None
_RAM = None


def load(snap=DEFAULT_SNAP):
    """Read the sine table (and keep the RAM for the object map) from a snapshot."""
    global _S, _RAM
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import gfxview
    _RAM = bytes(gfxview.load_ram(snap)[0])
    _S = struct.unpack('>1024h', _RAM[0xd0fa:0xd0fa + 2048])
    return _S


def table():
    if _S is None:
        load()
    return _S


def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


def w(v):
    return v & 0xffff


def _sin(a):
    return table()[(w(a) >> 5 & 0xfffe) // 2]


def matrix(a0, a1):
    """$1f646 as virus_flight.py models it: dict offset -> unsigned word of the matrix at $270d4."""
    cos0 = _sin(a0 + 0x4000); cos1 = _sin(a1 + 0x4000); s0 = _sin(a0); s1 = _sin(a1)
    hi = lambda x, y: w(((x * y) >> 16) * 2)       # muls ; swap ; add.w D,D
    m = {}
    m[14] = hi(s0, s1); m[0] = hi(cos0, cos1)
    m[12] = w(-hi(cos0, s1)); m[2] = w(-hi(s0, cos1))
    m[6] = w(s0); m[4] = w(s1); m[8] = w(cos0); m[16] = w(cos1); m[10] = 0
    return m


def thrust_column(a0, a1):
    """Signed high bytes of matrix words +2, +8, +14: the acceleration is -(column >> 3) per tick."""
    m = matrix(a0, a1)
    return [struct.unpack('>b', bytes([(m[o] >> 8) & 0xff]))[0] for o in (2, 8, 14)]


def step_full(pos, vel, att, d0, d1, d2, g, fuel=0x7fff):
    """One free-flight tick ($255d4 .. $257e6). Does not test the ground: see classify()."""
    d0 = w(d0); d1 = w(d1); d2 = w(d2)
    ceiling = s16(pos[1]) < s16(0xc900)            # $255d4: cmpi.w #$c900,y / bge ; bclr #1,D2
    if ceiling:
        d2 &= ~2
    new = []
    for a, t in zip(att, (d0, d1)):
        d5 = s16(a - t)                            # word subtract, wraps
        if d5 >= 0 and d5 >= 0x2800:               # only the positive side is clamped (bcc is unsigned)
            d5 = 0x2800
        d5 >>= 1
        new.append(s16(a - d5))
    v = [s16(x - (s16(x) >> 6)) for x in vel]      # drag 1/64
    thrust = bool(d2 & 2)
    fuel_out = False
    if thrust:
        if fuel - 3 < 0:                           # $25690 bpl: no thrust this tick, fuel := 0
            fuel = 0; thrust = False; fuel_out = True
        else:
            fuel -= 3
            col = thrust_column(new[0], new[1])
            v = [s16(x - (c >> 3)) for x, c in zip(v, col)]
    if d2 & 1:                                     # fire: one unit of fuel, a bullet ($202fc); no effect on the ship
        fuel = fuel - 1 if fuel - 1 >= 0 else 0
    p = [s16(a + b) for a, b in zip(pos, v)]
    vy_pre = v[1]
    v[1] = s16(v[1] + g)
    return {'pos': p, 'vel': v, 'att': new, 'fuel': fuel, 'thrust': thrust, 'ceiling': ceiling,
            'fuel_out': fuel_out, 'vy_pre': vy_pre}


def step(pos, vel, att, d0, d1, d2, g):
    r = step_full(pos, vel, att, d0, d1, d2, g)
    return r['pos'], r['vel'], r['att']


def ground(x, z):
    """D1 from $245b8(D6 = x, D7 = z), landscape 0 (the instruction words in f1.snap: asr.l #7, neg.w, nop,
    addi.w #$520). The pad (x and z both below $900, unsigned) is $420; water is the clamp $560."""
    x = w(x); z = w(z)
    if x < 0x900 and z < 0x900:
        return 0x420
    S = table()
    s = lambda ang, sh: S[w(ang) >> 6] >> sh
    D4 = w(x * 2); D5 = w(z * 2); D2 = w(D4 * 2); D3 = w(D5 * 2)
    a1 = s(x - D5, 0) + s(D4 + z + x, 0) + s(D5 - D4 + z, 0) + s(D2 - D3 - z, 1) + s(D5 - D2 - x, 1)
    a1 += s(D2 + D4 + D3 + z, 1)
    dd = w(2 * D2 + x + D4)
    a1 += s(dd - D3 - D5 - z, 2) + s(2 * D3 + dd + D5 + z, 2)
    d1 = s16(-s16(a1 >> 7))
    d1 = s16(d1 + 0x520)
    if d1 > 0x560:
        d1 = 0x560
    return d1


def clearance(pos):
    """D7 at $2580e: ground - $56 - y as a signed word. < 0: ground contact ($25870); 0..$170: the object-map test
    ($2581a); > $170: free ($2587c)."""
    return s16(ground(pos[0], pos[2]) - 0x56 - pos[1])


def object_cell(pos):
    """Address of the object-map byte the tick tests at $2581a..$25838."""
    return 0x32a58 + (w(pos[0] + 0x80) >> 8) + (w(pos[2] + 0x80) & 0xff00)


def classify(pos_after, objmap=None):
    """Which branch the tick takes after the position update, from the new position alone.
    'free': clearance > $170. 'low': 0 <= clearance <= $170 (safe only when the object cell's low 5 bits are 0 or its
    bit 4 is set; with objmap, a callable addr -> byte, returns 'low' or 'object'). 'ground': clearance < 0."""
    c = clearance(pos_after)
    if c < 0:
        return 'ground'
    if c > 0x170:
        return 'free'
    if objmap is not None:
        b = objmap(object_cell(pos_after))
        if b & 0x1f and not b & 0x10:
            return 'object'
    return 'low'


def snap_objmap(addr):
    if _RAM is None:
        load()
    return _RAM[addr]


SHIP_SHAPE = 0xab62


def ship_vertices():
    """The ship shape's vertices ($ab62: word +2 = count - 1, 3 signed words each from +8), from the snapshot."""
    if _RAM is None:
        load()
    n = struct.unpack('>H', _RAM[SHIP_SHAPE + 2:SHIP_SHAPE + 4])[0] + 1
    return [struct.unpack('>3h', _RAM[SHIP_SHAPE + 8 + 6 * i:SHIP_SHAPE + 14 + 6 * i]) for i in range(n)]


def vertex_margins(pos, att):
    """The ship's drawing routine ($2629c..$264b6, shape $ab62) rotates each vertex by the matrix, takes the ground
    height under that vertex ($245b8) and sets $62a61 -> $62a62 when the vertex is below it; the next tick then takes
    the crash exit ($257fe). Returns, per vertex, ground - vertex y as the game compares them (hit when < 0).
    pos, att: the state after a tick (what the next arrival at $255d4 reads)."""
    m = matrix(att[0], att[1])
    mw = [s16(m[o]) for o in range(0, 18, 2)]
    h2 = lambda a, b: s16(((a * b) >> 16) * 2)
    camy = 0x200 if pos[1] >= 0x100 else s16(pos[1] + 0x100)       # $25888..$25896
    rely = s16(pos[1] - camy)
    out = []
    for vx, vy, vz in ship_vertices():
        rx = s16(h2(mw[0], vx) + h2(mw[1], vy) + h2(mw[2], vz))
        ry = s16(h2(mw[3], vx) + h2(mw[4], vy) + h2(mw[5], vz))
        rz = s16(h2(mw[6], vx) + h2(mw[7], vy) + h2(mw[8], vz))
        lhs = s16(rely + ry)                                        # D3
        rhs = s16(ground(pos[0] + rx, pos[2] + rz) - camy)          # D1 after sub.w $270d0
        out.append(rhs - lhs)
    return out


def ship_hits_ground(pos, att):
    return min(vertex_margins(pos, att)) < 0


def step_game(st, u, objmap=snap_objmap):
    """One whole tick with the ground, landing and pad paths, on a state dict
    {pos, vel, att, g, fuel, latch ($62a63, nonzero in flight), contact ($62a62, nonzero after a vertex touched)}.
    Returns (new state, outcome): outcome is 'free', 'low', 'landed', 'pad' or a death: 'dead:ground' (hard or
    off-pad contact, $25870/$25c28), 'dead:object' ($25846), 'dead:vertex' ($257fe, flag from the previous draw).
    Deaths return the state unchanged apart from nothing: the game then runs its explosion and respawn (not modelled).
    Not modelled: enemies acting on the ship ($62a5d, the attractor's pull and fuel drain), the object map changing
    after the snapshot. The landing and pad branches are from the listing; check_landing.py is their run."""
    d0, d1, d2 = (w(x) for x in u)
    pos, vel, att, g, fuel = list(st['pos']), list(st['vel']), list(st['att']), st['g'], st['fuel']
    latch = st.get('latch', 0xff)
    if s16(pos[1]) < s16(0xc900):
        d2 &= ~2
    on_pad = not (d2 & 2) and not latch
    if on_pad:                                   # $25a6e: refuel, hold the pad height, attitude left as it is
        if s16(fuel + 0x19) <= 0x1000:
            fuel = fuel + 0x19
        pos[1] = 0x3ca; vel[1] = s16(-g)
        r = step_full(pos, vel, att, att[0], att[1], d2 & 1, g, fuel)
        r['att'] = list(att)
    else:
        latch = 0xff
        r = step_full(pos, vel, att, d0, d1, d2, g, fuel)
    new = dict(pos=r['pos'], vel=r['vel'], att=r['att'], g=g, fuel=r['fuel'], latch=latch, contact=0)
    if st.get('contact'):
        return dict(st), 'dead:vertex'
    c = clearance(new['pos'])
    outcome = 'pad' if on_pad else 'free'
    if c < 0:
        vy = new['vel'][1]
        if vy > 0x28:
            return dict(st), 'dead:ground'
        tot = s16(vy + abs(new['vel'][0]) + abs(new['vel'][2]))
        if tot > 0x28 or w(new['pos'][0]) >= 0x800 or w(new['pos'][2]) >= 0x800:
            return dict(st), 'dead:ground'
        new['pos'][1] = 0x3ca; new['vel'] = [0, 0, 0]; new['latch'] = 0
        outcome = 'landed'
    elif c <= 0x170:
        b = objmap(object_cell(new['pos'])) if objmap else 0
        if b & 0x1f and not b & 0x10:
            return dict(st), 'dead:object'
        if not on_pad:
            outcome = 'low'
    new['contact'] = 0xff if ship_hits_ground(new['pos'], new['att']) else 0
    return new, outcome
