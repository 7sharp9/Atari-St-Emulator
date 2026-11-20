"""Model of Virus's enemy shot: the fire routine `$22e38` (Enemy_Fire) with the spawn `$203f0` (EnemyShot_Spawn) and the shot's
object-walker handler `$20310` (EnemyShot).  Read from the bodies, gated by gate_eshot.py against natural captures (cap_eshot.py).

Fire `$22e38` (entered with A3 = the actor record in the walker's frame, already moved, thrust and pulled; A1 = the attitude
matrix whose words +0, +6, +12 are the nose; $62a5e is the ship-crashing byte):
  crashing: return, nothing happens (no draw).
  else: m_i = word(matrix, 0/6/12) >> 7 (asr.w #7 of the whole word), position = record pos + m, velocity = record vel + m,
  then `$203f0`: D3 = $e (jitter shift), A3 = $16 (life), D4 = 0 (no life jitter), A4 = `$20310`, `bra $1fc90`.
  `$1fc90` draws three words from the RNG ($2706e/$27072, shot.rng_draw), one per axis (x, y, z in that order), each
  `asr.w #14` = -2..1, added to BOTH the position and the velocity of that axis; `$1fd14` appends the 18-byte record
  (x y z vx vy vz life handler) to the OBJECT pool $302f6 unless $32a3c >= $177 (the three draws are made anyway).
  Then `$22e76..$22eb8`: the sound `$1790c` when the Manhattan distance to the ship is <= $3700 (no RNG, gated: RNG after
  the spawn equals RNG at the return).  Three RNG draws per call, no more, no less.
Handler `$20310`, one object-walker pass (walker `$1fa94`: life -= 1, negative -> removed with no handler call;
  pos += vel):  vy += gravity $32a3a; the record is stored back; unless $62a5e: if each of ship - pos on x, y, z is in
  [-$60, $60) the shot hits: fuel -= $333, and when that borrows $62a5d := $ff and fuel := 0; the record is removed.
  Otherwise ground = `$245b8`(x, z) -> D1 height, D3 type; d6 = ground - y (signed word): d6 >= $170 the shot flies on (dot and
  shadow drawn); d6 < 0 reaches the ground, water (D3 = 8, splash `$1fe36`) or land (explosion `$1ff8a`), removed; 0 <= d6 < $170
  looks at the object-map byte b of the cell ((x + $80) >> 8, (z + $80) & $ff00): type (b & $1f) 0 flies on; bit 4 set (destroyed
  already) explodes `$1ff8a` and is removed; else bit 4 of the map byte is set and the shot is removed through `$20092` when
  bit 5 (infected) is set, else `$20218`.
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
d = here
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
ROOT = d
sys.path.insert(0, os.path.join(ROOT, 'reversing/virus/py/mpc'))
import shot as S
s16 = S.s16

HANDLER = 0x20310
LIFE = 0x16
OBJ_MAX = 0x177
FUEL_HIT = 0x333
HIT_BOX = 0x60
FAR = 0x170


def fire_step(rec, mat, crash, rng, nobj, control='none'):
    """rec: actor record [x y z vx vy vz life pad beh]; mat: the three matrix words; rng: (a, b).
    Returns (pre, post, new object record or None, rng after): pre = (pos, vel) before the jitter (the inputs of $203f0),
    post = the position after the jitter (D0..D2 at the return of $1fc90)."""
    if crash:
        return None, None, None, rng
    sh = 6 if control == 'mshift' else 7
    m = [s16(w) >> sh for w in mat]
    if control == 'nomuzzle':
        m = [0, 0, 0]
    pos = [s16(rec[i] + m[i]) for i in range(3)]
    vel = [s16(rec[3 + i] + m[i]) for i in range(3)]
    jsh = 13 if control == 'jit13' else 14
    js = []
    for _ in range(3):
        rng, d7 = S.rng_draw(rng)
        js.append(s16(d7) >> jsh)
    if control == 'draw4':
        rng, _d = S.rng_draw(rng)
    npos = [s16(pos[i] + js[i]) for i in range(3)]
    nvel = [s16(vel[i] + js[i]) for i in range(3)]
    life = 0x15 if control == 'life21' else LIFE
    obj = npos + nvel + [life, HANDLER] if nobj < OBJ_MAX else None
    return (pos, vel), npos, obj, rng


def in_box(dv, half):
    return ((dv + half) & 0xffff) < 2 * half


def handler_step(rec, ship, fuel, crash, g, gnd, cellbyte, control='none'):
    """rec: the record as the walker finds it [x y z vx vy vz life]; ship: (x, y, z); gnd(x, z) -> (D1, D3).
    Returns dict: out in expired | hit | fly | water | ground | wreck | fresh_inf | fresh_plain, plus stored (record written
    back by the handler), fuel, flag5d, cell (map byte after)."""
    x, y, z, vx, vy, vz, life = rec[:7]
    life -= 1
    if life < 0:
        return {'out': 'expired'}
    x, y, z = s16(x + vx), s16(y + vy), s16(z + vz)
    if control != 'nograv':
        vy = s16(vy + g)
    stored = [x, y, z, vx, vy, vz, life]
    half = 0x50 if control == 'box50' else HIT_BOX
    if not crash and all(in_box(ship[i] - p, half) for i, p in enumerate((x, y, z))):
        cost = 0x332 if control == 'cost332' else FUEL_HIT
        f = fuel - cost
        f5d = 0
        if f < 0:
            f, f5d = 0, 0xff
        return {'out': 'hit', 'stored': stored, 'fuel': f, 'flag5d': f5d}
    d1, d3 = gnd(x, z)
    far = 0x180 if control == 'far180' else FAR
    d6 = s16(d1 - y)
    r = {'stored': stored, 'd6': d6}
    if d6 >= far:
        r['out'] = 'fly'
    elif d6 < 0:
        r['out'] = 'water' if d3 == 8 else 'ground'
    else:
        b = cellbyte
        if b & 0x1f == 0:
            r['out'] = 'fly'
        elif b & 0x10:
            r['out'] = 'wreck'
        else:
            r['cell'] = b | 0x10
            r['out'] = 'fresh_inf' if b & 0x20 else 'fresh_plain'
            r['type'] = b & 0xf
    return r
