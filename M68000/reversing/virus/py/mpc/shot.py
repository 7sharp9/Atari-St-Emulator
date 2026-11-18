"""Exact integer model of the player's shot in Virus (Atari ST) and predictors for the wave-0 targets.

All quantities are signed 16-bit words as the game holds them; y grows downward. Gates: gate_shot.py (spawn, flight,
hit, terrain), gate_kill.py (award and removal), gate_actor.py (target predictors), gate_danger.py (ship box).

Frame order (main loop $231a8): object walker $1fa72 -> ship tick $255c2 (arrival at $255d4 = "tick k") -> actor
walker $2157c -> ... So, between arrival k and arrival k+1:
    1. ship tick k: a shot fired here is appended with life $16 at the ship's PRE-move position;
    2. actor walker: every actor moves; an actor whose life word has bit 15 takes its kill path here;
    3. object walker (next frame): every shot does life -= 1 (removed when negative), pos += vel, vy += g, then is
       tested against the actor pool as arrival k+1 will read it (first actor in pool order inside the box gets bit 15
       and the shot is removed), then against the ground and the object map.
So a shot fired in tick k appears at arrival k+1 already advanced once (life $15), and a hit made in step 3 shows at
arrival k+1 as bit 15 in the actor's life word; the award and the removal happen in tick k+1's actor walker and show
at arrival k+2.

    import shot
    rec, rng2 = shot.spawn(pos, vel, att_or_matrix, rng)      # exact, with the jitter; rng = (a, b) of $2706e/$27072
    rec = shot.spawn_nominal(pos, vel, att_or_matrix)         # no jitter; true record = nominal + j, j in JITTER
    rec, rng2, fuel2, dscore = shot.spawn_from_tick(st, u, rng, nobj)   # from the arrival state and controls
    rec2 = shot.fly(rec, g)                                   # None when it expires
    i = shot.hits(rec2, actors)                               # index of the actor hit, or None
    what = shot.terrain(rec2, objmap)                         # 'fly' | 'ground' | 'water' | 'object' | 'wreck'
    rec2, what, i = shot.step(rec, g, actors, objmap)         # the three in the game's order
    shot.targets(pool) ; shot.predict(actor, n, ...) ; shot.actor_step(actor, ...)
"""
import os
import struct
import sys

_d = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _d)
import exact  # noqa: E402  (the gated ship tick: matrix, ground, step_full)

ROOT = exact.ROOT
SNAP = os.path.join(ROOT, 'scratchpad', 'virus', 'demo', 'S1b.snap')
M32 = 0xffffffff

LIFE = 0x16                 # A3 at $20300: the shot moves 22 times and is removed on the 23rd walker pass
HANDLER = 0x1feb0
JITTER = (-2, 1)            # word asr #14 of a random word: each axis, the SAME value added to pos and to vel
OBJ_MAX = 0x177             # $1fd1a: no record is appended at or above 375 objects (fuel, score, RNG still spent)
BOX = 0xa0                  # $1fee2: -$a0 <= actor - shot < $a0 on x, z, y
SHIP_BOX = 0xc0             # $21622: -$c0 <= ship - actor < $c0 on x, y, z


def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


def s8(v):
    v &= 0xff
    return v - 0x100 if v & 0x80 else v


# ---------------------------------------------------------------- RNG ($1fc90, state longs $2706e and $27072)
def rng_draw(state):
    """One draw: returns (new state, D7) where D7 = swap(old a); a += b; b = D7."""
    a, b = state
    d7 = ((a << 16) | (a >> 16)) & M32
    return ((a + b) & M32, d7), d7


def rng_from_hex(h):
    return struct.unpack('>2L', bytes.fromhex(h))


def rng_skip(state, n):
    for _ in range(n):
        state, _v = rng_draw(state)
    return state


def jitter3(state, shift=14):
    """The three per-axis draws of $1fc90 with D3 = shift: word asr."""
    js = []
    for _ in range(3):
        state, d7 = rng_draw(state)
        js.append(s16(d7) >> shift)
    return state, js


# ---------------------------------------------------------------- spawn ($25762..$2578e, $202fc, $1fc90, $1fd14)
def nose(att_or_matrix):
    """Signed high bytes of matrix words +0, +6, +12 at $270d4. Accepts (att0, att1), the dict exact.matrix()
    returns, or the 18 raw bytes."""
    m = att_or_matrix
    if isinstance(m, (bytes, bytearray)):
        return [s8(m[0]), s8(m[6]), s8(m[12])]
    if isinstance(m, dict):
        return [s8(m[o] >> 8) for o in (0, 6, 12)]
    m = exact.matrix(m[0], m[1])
    return [s8(m[o] >> 8) for o in (0, 6, 12)]


def spawn_nominal(pos, vel, att_or_matrix):
    """pos: the ship's position at arrival (before this tick's move). vel: the ship's velocity after this tick's
    drag and thrust and before gravity (D3..D5 at $2577e). att_or_matrix: the attitude AFTER this tick's turn."""
    n = nose(att_or_matrix)
    return [s16(p + c) for p, c in zip(pos, n)] + [s16(v + c) for v, c in zip(vel, n)] + [LIFE]


def spawn(pos, vel, att_or_matrix, rng):
    """Exact record as $1fd14 appends it, and the RNG state after the three draws."""
    r = spawn_nominal(pos, vel, att_or_matrix)
    rng, j = jitter3(rng)
    return [s16(r[i] + j[i]) for i in range(3)] + [s16(r[3 + i] + j[i]) for i in range(3)] + [LIFE], rng


EXHAUST_DRAWS = 20          # thrust: 5 x $1fdca, each 3 jitter draws + 1 life draw (D4 = 6), before the fire code


def spawn_from_tick(st, u, rng, nobj=0):
    """st: {pos, vel, att, g, fuel, latch?} at arrival k; u: [D0, D1, D2] used this tick; rng: state at arrival k.
    Returns (record or None, rng after the tick's own draws, fuel after, score delta). None when the fire bit is
    clear, the fuel is short, or the object pool is full. The RNG return covers only the ship tick's draws (exhaust
    and shot); the walkers draw more before the next arrival."""
    d0, d1, d2 = (x & 0xffff for x in u)
    pos, vel, att, g, fuel = st['pos'], st['vel'], st['att'], st['g'], st['fuel']
    latch = st.get('latch', 0xff)
    if s16(pos[1]) < s16(0xc900):
        d2 &= ~2
    if not (d2 & 2) and not latch:                       # on the pad ($25a6e): attitude held, refuel
        if s16(fuel + 0x19) <= 0x1000:
            fuel += 0x19
        pos = [pos[0], 0x3ca, pos[2]]; vel = [vel[0], s16(-g), vel[2]]
        r = exact.step_full(pos, vel, att, att[0], att[1], d2 & 1, g, fuel)
        r['att'] = list(att)
    else:
        r = exact.step_full(pos, vel, att, d0, d1, d2, g, fuel)
    if r['thrust']:
        rng = rng_skip(rng, EXHAUST_DRAWS)
    if not d2 & 1:
        return None, rng, r['fuel'], 0
    fuel_before_fire = fuel - 3 if r['thrust'] else (0 if r['fuel_out'] else fuel)
    if fuel_before_fire - 1 < 0:
        return None, rng, 0, 0
    v = [r['vel'][0], r['vy_pre'], r['vel'][2]]
    rec, rng = spawn(pos, v, r['att'], rng)              # the draws are made even when the pool is full
    if nobj >= OBJ_MAX:
        rec = None
    return rec, rng, fuel_before_fire - 1, -1


# ---------------------------------------------------------------- flight (walker $1fa94, handler $1feb0)
def fly(rec, g):
    """One object-walker pass: life -= 1, removed if negative; pos += vel; vy += g. Returns the stored record."""
    x, y, z, vx, vy, vz, life = rec
    life -= 1
    if life < 0:
        return None
    return [s16(x + vx), s16(y + vy), s16(z + vz), vx, s16(vy + g), vz, life]


def in_box(d, half):
    """The game's `sub ; addi #half ; cmp #2*half ; bcc`: true for -half <= d < half (word arithmetic)."""
    return ((d + half) & 0xffff) < 2 * half


def hits(rec, actors):
    """rec: the shot AFTER fly(). actors: pool records in pool order, each starting x, y, z (the pool as the next
    arrival reads it). No record is skipped: a waiting record (y = $f100) or the player's rocket stops a shot too.
    Returns the index of the first actor inside the box, tested x then z then y, or None."""
    x, y, z = rec[0], rec[1], rec[2]
    for i, a in enumerate(actors):
        if in_box(a[0] - x, BOX) and in_box(a[2] - z, BOX) and in_box(a[1] - y, BOX):
            return i
    return None


_PAD_T = None


def ground_type(x, z):
    """(height, type) as $245b8 returns them in D1, D3: 9 land at or above $510, 7 shore, 8 water (the $560 clamp)."""
    h = exact.ground(x, z)
    xu = x & 0xffff; zu = z & 0xffff
    if xu < 0x900 and zu < 0x900:
        return h, None                                    # pad: D3 from the table at $246ba (never 8 there: read)
    # recompute the unclamped height to tell 7 from 8
    S = exact.table()
    s = lambda ang, sh: S[(ang & 0xffff) >> 6] >> sh
    D4 = (xu * 2) & 0xffff; D5 = (zu * 2) & 0xffff; D2 = (D4 * 2) & 0xffff; D3 = (D5 * 2) & 0xffff
    a1 = s(xu - D5, 0) + s(D4 + zu + xu, 0) + s(D5 - D4 + zu, 0) + s(D2 - D3 - zu, 1) + s(D5 - D2 - xu, 1)
    a1 += s(D2 + D4 + D3 + zu, 1)
    dd = (2 * D2 + xu + D4) & 0xffff
    a1 += s(dd - D3 - D5 - zu, 2) + s(2 * D3 + dd + D5 + zu, 2)
    d1 = s16(s16(-s16(a1 >> 7)) + 0x520)
    return h, (9 if d1 <= 0x510 else 8 if d1 > 0x560 else 7)


def obj_cell(x, z):
    """Index into the object map $32a58 (64K bytes) of the cell the shot tests ($1ff40..$1ff5c)."""
    return (((x + 0x80) & 0xffff) >> 8) + ((z + 0x80) & 0xff00)


def terrain(rec, objmap=None):
    """rec: the shot AFTER fly(), not hitting an actor. objmap: bytes-like of 65536 (the map at $32a58) or None.
    'fly': it stays. 'ground' / 'water': below the ground height (explosion / splash), removed.
    'wreck': within $170 above the ground over a cell whose object is already destroyed (bit 4), removed.
    'object': the same over a live object: the cell's bit 4 is set, removed; awards: 40 if the cell has bit 5
    (infected) and type < 4, 1000 if type $c (the object is erased) -- awards read, not gated here.
    Without objmap the object test is skipped ('fly')."""
    x, y, z = rec[0], rec[1], rec[2]
    h, t = ground_type(x, z)
    d6 = s16(h - y)
    if d6 >= 0x170:
        return 'fly'
    if d6 < 0:
        return 'water' if t == 8 else 'ground'
    if objmap is None:
        return 'fly'
    b = objmap[obj_cell(x, z)]
    if b & 0x1f == 0:
        return 'fly'
    return 'wreck' if b & 0x10 else 'object'


def step(rec, g, actors, objmap=None):
    """One walker pass in the game's order. Returns (record or None, what, actor index or None); what is 'fly',
    'expired', 'hit', 'ground', 'water', 'object' or 'wreck'. actors: the pool as the NEXT arrival reads it."""
    r = fly(rec, g)
    if r is None:
        return None, 'expired', None
    i = hits(r, actors)
    if i is not None:
        return None, 'hit', i
    w = terrain(r, objmap)
    return (r if w == 'fly' else None), w, None


def muzzle(att_or_matrix):
    """The shot's velocity relative to the ship before jitter (units per tick, at most 127 per axis)."""
    return nose(att_or_matrix)


# ---------------------------------------------------------------- actors (pool $31d54, 20-byte records)
B_WAIT_CHASER, B_CHASER = 0x21ae2, 0x21afe
B_WAIT_SEEDER, B_SEEDER_FLY, B_SEEDER_DESCEND, B_SEEDER_LANDED, B_SEEDER_TAKEOFF = \
    0x21776, 0x21792, 0x21894, 0x21976, 0x219de
B_WAIT_PATROL, B_PATROL_CRUISE, B_PATROL_HOME, B_PATROL_ATTACK = 0x21c42, 0x21c64, 0x21d08, 0x21df6

# behaviour -> (kind, state, award for a hit, can a shot's bit 15 take effect)
KINDS = {
    B_WAIT_CHASER: ('chaser', 'wait', 0, False),
    B_CHASER: ('chaser', 'live', 400, True),
    B_WAIT_SEEDER: ('seeder', 'wait', 0, False),
    B_SEEDER_FLY: ('seeder', 'fly', 100, True),
    B_SEEDER_DESCEND: ('seeder', 'descend', 100, True),
    B_SEEDER_LANDED: ('seeder', 'landed', 50, True),
    B_SEEDER_TAKEOFF: ('seeder', 'takeoff', 100, True),
    B_WAIT_PATROL: ('patrol', 'wait', 0, False),
    B_PATROL_CRUISE: ('patrol', 'cruise', 300, True),
    B_PATROL_HOME: ('patrol', 'home', 300, True),
    B_PATROL_ATTACK: ('patrol', 'attack', 300, True),
    0x21f00: ('pursuer', 'live', 500, True),     # a provoked patrol ($201b4); award read from behaviours.md, not modelled
}


def unpack_pool(raw):
    """raw: bytes or hex of n 20-byte records -> list of [x, y, z, vx, vy, vz, life, pad, behaviour]."""
    if isinstance(raw, str):
        raw = bytes.fromhex(raw)
    return [list(struct.unpack('>8hL', raw[i:i + 20])) for i in range(0, len(raw), 20)]


def unpack_obj(raw):
    """n 18-byte object records -> list of [x, y, z, vx, vy, vz, life, handler]."""
    if isinstance(raw, str):
        raw = bytes.fromhex(raw)
    return [list(struct.unpack('>7hL', raw[i:i + 18])) for i in range(0, len(raw), 18)]


def targets(pool):
    """For each pool record: dict(index, kind, state, award, hittable, hits_to_kill). In wave 0 every hittable
    record dies on the first hit (the kill path runs in the next actor walker); a waiting record still stops the
    shot but clears bit 15 itself."""
    out = []
    for i, a in enumerate(pool):
        kind, state, award, can = KINDS.get(a[8], ('other', hex(a[8]), None, None))
        out.append({'index': i, 'kind': kind, 'state': state, 'award': award, 'hittable': can,
                    'hits_to_kill': 1 if can else None, 'pos': a[:3], 'vel': a[3:6]})
    return out


_HMAP = None


def load_hmap(snap=SNAP):
    global _HMAP
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import gfxview
    ram = bytes(gfxview.load_ram(snap)[0])
    _HMAP = ram[0x42a58:0x52a58]
    return _HMAP


def aground(x, z):
    """The actor walker's ground height ($24754): one byte per $100 cell of the height map $42a58, no
    interpolation; the pad (x and z below $900) is $420."""
    if _HMAP is None:
        load_hmap()
    x &= 0xffff; z &= 0xffff
    if x < 0x900 and z < 0x900:
        return 0x420
    return s16((_HMAP[(x >> 8) + (z & 0xff00)] << 3) + 0xfd68)


def man(a, b):
    """The game's saturating |dx| + |dy| + |dz| ($21c74..$21ca0), each difference a wrapped word."""
    t = 0
    for i in range(3):
        d = s16(a[i] - b[i])
        d = -d if d < 0 else d            # neg.w of $8000 stays $8000 (negative): handled by the overflow test
        if d == 0x8000:
            return 0x7fff
        t += d
        if t > 0x7fff:
            return 0x7fff
    return t


def _dot(m, offs, d):
    t = 0
    for o, dv in zip(offs, d):
        t += (((s16(m[o]) >> 1) * dv) >> 16) * 2          # asr.w #1 ; muls ; swap ; add.w D,D
    return s16(t)


def _tilt(pad, up):
    t = pad & 0xff
    t = min(t + 2, 0x3f) if up else max(t - 2, 0)
    return (pad & 0xff00) | t


def patrol_steer(pos, tgt, lw, pad, gh):
    """$22c1e: returns (matrix from the OLD attitude, life word, pad word). pad: low byte = tilt 0..$3f (x $100 is
    the tilt angle), whole word = heading. Life-word bits: 11 nose-down/no thrust, 12 turn direction, 10 ceiling."""
    m = exact.matrix((pad & 0xff) << 8, pad)
    d = [s16(pos[i] - tgt[i]) >> 1 for i in range(3)]
    if s16(gh - pos[1]) >= 0x200 and _dot(m, (2, 8, 14), d) < 0:
        lw |= 0x800; pad = _tilt(pad, True)
    else:
        lw &= ~0x800; pad = _tilt(pad, False)
    if _dot(m, (4, 10, 16), d) < 0:
        lw |= 0x1000; pad = (pad - 0x700) & 0xffff
    else:
        lw &= ~0x1000; pad = (pad + 0x700) & 0xffff
    lw &= ~0x400
    if pos[1] < s16(0xc900):
        lw |= 0xc00
    return m, lw, pad


def patrol_hold(lw, pad):
    """$22d04: keep turning the way the last steer decided."""
    m = exact.matrix((pad & 0xff) << 8, pad)
    pad = _tilt(pad, bool(lw & 0x800))
    pad = (pad - 0x700) & 0xffff if lw & 0x1000 else (pad + 0x700) & 0xffff
    return m, lw, pad


def patrol_thrust(m, vel):
    """$22d5e: vel -= c >> 4 and c >> 5 of the matrix column (+2, +8, +14), and n >> 5 of the column (+0, +6, +12)."""
    out = []
    for v, oc, on in zip(vel, (2, 8, 14), (0, 6, 12)):
        c = s8(m[oc] >> 8) >> 4
        v = v - c - (c >> 1) - (s8(m[on] >> 8) >> 5)
        out.append(s16(v))
    return out


def _patrol_fly(x, y, z, vx, vy, vz, lw, pad, gh, tgt, steer, g, near):
    x, y, z = s16(x + vx), s16(y + vy), s16(z + vz)
    vy = s16(vy + g)
    vx, vy, vz = (s16(v - (v >> 5)) for v in (vx, vy, vz))
    if steer:
        m, lw, pad = patrol_steer((x, y, z), tgt, lw, pad, gh)
    else:
        m, lw, pad = patrol_hold(lw, pad)
    if not lw & 0x800:
        vx, vy, vz = patrol_thrust(m, (vx, vy, vz))
    if s16(gh - y) <= near:
        vx, vy, vz = patrol_thrust(m, (vx, vy, vz))
    return x, y, z, vx, vy, vz, lw, pad


def actor_step(a, ship=None, rng=None, tick48=None, g=3, queue0=None):
    """One actor-walker pass for a wave-0 record [x, y, z, vx, vy, vz, life, pad, behaviour].
    Returns (new record or None when it dies this pass, info). info: 'killed' (bit 15 was set: award KINDS[..]),
    'grounded' (the walker found the ground at or above it: it dies with the same award), 'rng' (the take-off drew
    its new velocity: exact only when rng is the state at that moment), 'unmodelled' (an input the state needs was
    not given, or the chaser), or None.
      ship    the ship's position AFTER this tick's move (the patrol reads it: range tests and the attack target)
      tick48  the word $32a48 this record sees: ($32a44 at the arrival) + (pool index) + 1, plus 1 for every record
              removed earlier in the same pass; only its low two bits matter (the patrol steers when they are 0)
      queue0  the three words at $27134 (the patrol's homing target), as read at the arrival"""
    x, y, z, vx, vy, vz, life, pad, b = a
    gh = aground(x, z)
    lw = life & 0xffff
    pad &= 0xffff
    if gh <= y:
        lw |= 0xa000
    info = None
    if b in (B_WAIT_SEEDER, B_WAIT_CHASER, B_WAIT_PATROL):
        lw &= 0x7fff
        n = s16(lw - 1)
        if n >= 0:
            return [x, y, z, vx, vy, vz, n, s16(pad), b], None
        if b == B_WAIT_CHASER:
            return [x, y, z, vx, vy, vz, 0x1ff, s16(pad), B_CHASER], 'unmodelled'
        if b == B_WAIT_PATROL:
            b = B_PATROL_CRUISE; lw = 0x4040; pad = 0
        else:
            b = B_SEEDER_FLY; lw = 0
    if lw & 0x8000:
        return None, ('grounded' if lw & 0x2000 else 'killed')
    life = s16(lw)
    if b == B_SEEDER_FLY:
        x, y, z = s16(x + vx), s16(y + vy), s16(z + vz)
        if life:
            life -= 1
        elif gh <= 0x320:
            b = B_SEEDER_DESCEND
        vy = s16(vy - (s16(y - gh + 0x280) >> 5))
        vy = s16(vy - (vy >> 4))
        if vy >= 0:
            vy = min(vy, 0x60)
        elif vy <= -0x60:
            vy = -0x60
    elif b == B_SEEDER_DESCEND:
        x, y, z = s16(x + vx), s16(y + vy), s16(z + vz)
        vx = s16(vx - (vx >> 4)); vz = s16(vz - (vz >> 4))
        d4 = s16(gh - y)
        if d4 <= 0x86:
            b = B_SEEDER_LANDED
            y = s16(exact.ground(x, z) - 0x86)
            life = 0x200
        vy = d4 >> 5
    elif b == B_SEEDER_LANDED:
        life -= 1
        if life < 0:
            life = 0x64; vy = -0x10; b = B_SEEDER_TAKEOFF
    elif b == B_SEEDER_TAKEOFF:
        y = s16(y + vy)
        if s16(gh - y) >= 0x1c0:
            b = B_SEEDER_FLY; info = 'rng'
            if rng is not None:
                rng, d = rng_draw(rng); vx = s8(d) >> 1
                rng, d = rng_draw(rng); vz = s8(d) >> 1
    elif b in (B_PATROL_CRUISE, B_PATROL_HOME, B_PATROL_ATTACK):
        if b == B_PATROL_CRUISE:
            if ship is None:
                info = 'no ship given: the range test was skipped'
            elif man((x, y, z), ship) <= 0x2800:
                b = B_PATROL_ATTACK
        if b == B_PATROL_CRUISE:
            lo = ((lw & 0xff) - 1) & 0xff
            if lo == 0:
                lo = 0x40; b = B_PATROL_HOME
            lw = (lw & 0xff00) | lo
            x = s16(x + vx); z = s16(z + vz)
            d7 = s16(gh - 0x400)
            if d7 <= y:
                y = d7
        elif tick48 is None or (b == B_PATROL_ATTACK and ship is None) or (b == B_PATROL_HOME and queue0 is None):
            return list(a), 'unmodelled'
        elif b == B_PATROL_HOME:
            lo = ((lw & 0xff) - 1) & 0xff
            if lo == 0:
                lo = 5; b = B_PATROL_CRUISE
            lw = (lw & 0xff00) | lo
            x, y, z, vx, vy, vz, lw, pad = _patrol_fly(x, y, z, vx, vy, vz, lw, pad, gh, queue0, tick48 & 3 == 0,
                                                       g, 0x300)
        else:
            x, y, z, vx, vy, vz, lw, pad = _patrol_fly(x, y, z, vx, vy, vz, lw, pad, gh, ship, tick48 & 3 == 0,
                                                       g, 0x280)
            if man((x, y, z), ship) > 0x2300:
                lw = (lw & 0xff00) | 5; b = B_PATROL_CRUISE
        life = s16(lw)
    else:
        return list(a), 'unmodelled'
    return [x, y, z, vx, vy, vz, life, s16(pad), b], info


def predict(a, n, ship=None, g=3, tick48=None, queue0=None, ship_path=None):
    """Positions of one actor over the next n actor-walker passes: list of n [x, y, z] (entry j = the position
    arrival k+1+j reads, the one a shot's walker pass just before that arrival is tested against), cut short if it
    dies. Seeder states and the patrol's cruise are exact while no RNG draw (take-off) happens. The patrol's homing
    and attack states are exact when tick48 (this record's value for the first pass; it advances by 1 a tick while
    the pool is not reordered), queue0 and the ship's future positions are right: ship_path[j] = the ship's position
    after tick k+j's move (or one fixed `ship`). Without tick48 they fall back to pos += vel with gravity and the
    1/32 drag (no steering or thrust)."""
    out = []
    a = list(a)
    for j in range(n):
        sp = ship_path[min(j, len(ship_path) - 1)] if ship_path else ship
        r, info = actor_step(a, ship=sp, g=g, tick48=None if tick48 is None else tick48 + j, queue0=queue0)
        if r is None:
            break
        if info == 'unmodelled':
            x, y, z, vx, vy, vz = a[:6]
            x, y, z = s16(x + vx), s16(y + vy), s16(z + vz)
            vy = s16(vy + g)
            vx, vy, vz = (s16(v - (v >> 5)) for v in (vx, vy, vz))
            r = [x, y, z, vx, vy, vz] + a[6:]
        a = r
        out.append(a[:3])
    return out


# ---------------------------------------------------------------- danger (common tail $215ea..$21654)
def ship_hit(ship_after, actor_after):
    """True when the actor walker's common tail flags the ship: -$c0 <= ship - actor < $c0 on x, y and z, with the
    ship's position after tick k's move and the actor's after the same tick's walker pass. Applies to behaviours
    that end at $215ea (not a waiting record, not the patrol's cruise); the ship then dies in tick k+1 ($257fa)."""
    return all(in_box(ship_after[i] - actor_after[i], SHIP_BOX) for i in range(3))
