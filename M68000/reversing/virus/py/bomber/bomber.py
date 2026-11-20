"""The Virus bomber `$222dc` / `$22316`, the bomb spawn `$2086a`, the bomb handler `$207d6`, its burst `$2012c`, and the plant
`$205f6` / `$206b8` / `$2010a`, as Python step functions. Read from the bodies (disassembly), gated by gate_bomber.py.

Actor walker `$2157c` hands the behaviour D0..D2 = x y z, D3..D5 = vx vy vz, D6 = life word, D7 = ground height ($24754 at x, z),
A6 = record + 20; bits 15 and 13 of D6 are set first when ground <= y. The walker does NOT move the record; the behaviour does.

Bomber_Wait `$222dc`: life bit 15 cleared, life - 1; not negative: stored (pos, vel, pad untouched). Negative: behaviour := `$22316`, the
heading is `(RNG draw) & $ff` (one draw `$1fc90`-style: new a = a + b, new b = swap(old a), value = low word of swap(old a)), stored as
the life word, and the same pass runs the Bomber body.

Bomber `$22316`, per pass:
  life bit 15 set (hit, ship contact, or ground <= y): sound, award $320 (800), kill path `$216d6`; no move.
  heading h = life & $ff. `$1f646` builds a matrix at `$270d4` from D0 = 0, D1 = h << 8 (a side effect on the ship's matrix scratch,
  rebuilt by the ship tick; not modelled). The record's vx and vz are REPLACED by the high bytes (sign-extended) of matrix words 0
  and 6; vy keeps its value. x, y, z += those velocities (y += the old vy).
  spring: vy -= (y - ground + $700) >> 5, then vy -= vy >> 4, clamp to [-$60, $60]. The record is stored.
  dist = saturating |dx| + |dy| + |dz| from the NEW position to the ship words `$270b0` (the ship after this tick's move).
  dist <= $2d00 (near): sound; if tick $32a48 & 7 == 0 a bomb `$2086a`, EXCEPT dist > $a00 and ground == $560 (water level: no bomb).
      (the code ands the 16th-tick test onto a register that is already zero, so over land beyond $a00 the bomb is every 8th tick too.)
  dist >  $2d00 (far): when $32a48 & $f != 0 and ground != $560, `$2010a`: 21 plants.
  then the common tail `$215ea` (ship contact box, draw record), which is the actor walker's, not modelled here.

Bomb spawn `$2086a` -> `$1fc8c`: jitter shift 13 on each axis: three draws, word asr 13; position += j, velocity = (j0, $30 + j1, j2),
life $fa, handler `$207d6`; appended unless the object pool holds $177 records (the draws are spent either way).
Bomb_Fall `$207d6` (object walker: life - 1 first, negative removes; position += velocity; no gravity, no drag):
  ground - y <= $80 (signed): the burst `$2012c`.   else dist(ship) <= $400: fuel -= $333 (unsigned borrow: fuel := 0, `$62a5d` := $ff), the burst.
  else the record stays (drawn).
Burst `$2012c`: 31 drops when dist <= $2300 and the object pool holds more than $bb records, else 51; each drop `$20702`:
  dist > $2300: a jittered plant `$206b8` (two draws, asr 4 on x then z, then `$205f6` at the jittered x, z);
  else a falling infection `$205be` appended (three draws asr 10; velocity (j0, -$2a + j1, j2), life $80); the position registers keep the
  jitter from drop to drop (`$1fc8c` adds to D0..D2 and the caller does not restore them). Then the bomb is removed (`$1fc58`).
Plant `$205f6`: ground at the next cell corner ((x & $ff00) + $100, (z & $ff00) + $100) above $510 or equal $420: nothing; else bit 5 of the
  object-map byte at $32a58 + ((x + $80) >> 8) + ((z + $80) & $ff00); when that byte's low five bits are 1..3 the queue slot `$27146`
  takes (x, y - $b8, z). (A bitmap at `$2f6f6` is also written: outside the captures, not modelled.)
"""
import os, sys
_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, 'tools', 'rdis.py')):
    _p = os.path.dirname(_d)
    if _p == _d:
        raise SystemExit('repo root (the directory holding tools/rdis.py) not found')
    _d = _p
ROOT = _d
sys.path.insert(0, os.path.join(ROOT, 'reversing/virus/py'))
sys.path.insert(0, os.path.join(ROOT, 'reversing/virus/py/mpc'))
import shot as S
import exact
s16 = S.s16
rng_draw = S.rng_draw

B_WAIT, B_FLY, B_BOMB = 0x222dc, 0x22316, 0x207d6
B_DROP = 0x205be
OBJ_MAX = 0x177

_T = None
def sine():
    global _T
    if _T is None:
        _T = exact.table()
    return _T


def heading_vel(h, break_=None):
    """(vx, vz) the bomber takes from `$1f646` with D0 = 0, D1 = h << 8: sign-extended high bytes of matrix words 0 and 6."""
    T = sine()
    t = lambda v: T[(((v & 0xffff) >> 5) & 0xfffe) >> 1]
    d1 = (h << 8) & 0xffff
    d2 = t(0x4000); d3 = t(d1 + 0x4000)
    d1p = t(d1)
    w0 = s16(2 * s16((d2 * d3) >> 16))
    w6 = s16(-s16(2 * s16((d1p * d2) >> 16)))
    if break_ == 'swapaxes':
        w0, w6 = w6, w0
    return S.s8(w0 >> 8), S.s8(w6 >> 8)


def man(a, b):
    return S.man(a, b)


def bomber_events(dist, gh, t48, control=None):
    """(bomb, plants) for a pass that ended at distance dist from the ship over ground height gh."""
    water = gh == 0x560
    if dist <= 0x2d00:
        bomb = (t48 & 7) == 0
        if bomb and dist > 0xa00 and water:
            bomb = False
        if control == 'every16' and bomb and dist > 0xa00 and (t48 & 0xf) != 0:
            bomb = False                      # the reading in the table of behaviours.md ("every 16th tick over land")
        return bomb, False
    return False, (t48 & 0xf) != 0 and not water


def bomber_step(a, ship, t48, rng=None, control=None):
    """a = [x y z vx vy vz life pad behaviour] (signed words, behaviour long). Returns (record or None, info, rng, bomb, plants).
    info: None, 'killed' / 'grounded' (kill path, award 800, no move), 'rng' (hatch: needs rng, else the record is returned
    unchanged). bomb / plants: whether `$2086a` / `$2010a` run in this pass (position = the returned record's)."""
    x, y, z, vx, vy, vz, life, pad, b = a
    gh = S.aground(x, z)
    lw = life & 0xffff
    if gh <= y:
        lw |= 0xa000
    info = None
    if b == B_WAIT:
        lw &= 0x7fff
        n = s16(lw - 1)
        if n >= 0:
            return [x, y, z, vx, vy, vz, n, s16(pad), b], None, rng, False, False
        if rng is None:
            return list(a), 'rng', rng, False, False
        rng, d = rng_draw(rng)
        lw = d & 0xff
        b = B_FLY
    if lw & 0x8000:
        return None, ('grounded' if lw & 0x2000 else 'killed'), rng, False, False
    vx, vz = heading_vel(lw & 0xff, control)
    x, y, z = s16(x + vx), s16(y + vy), s16(z + vz)
    d1 = s16(y - gh + (0x700 if control != 'spring6c' else 0x6c0)) >> (5 if control != 'spring4' else 4)
    vy = s16(vy - d1)
    vy = s16(vy - (vy >> 4))
    if vy < 0:
        if vy <= -0x60:
            vy = -0x60
    elif vy >= 0x60:
        vy = 0x60
    dist = man((x, y, z), ship)
    bomb, plants = bomber_events(dist, gh, t48, control)
    return [x, y, z, vx, vy, vz, s16(lw), s16(pad), b], info, rng, bomb, plants


def bomb_spawn(pos, rng, nobj, control=None):
    """The `$2086a` append: (record or None, rng after its three draws)."""
    j = []
    for _ in range(3):
        rng, d = rng_draw(rng)
        j.append(s16(d) >> (13 if control != 'jit12' else 12))
    rec = [s16(pos[0] + j[0]), s16(pos[1] + j[1]), s16(pos[2] + j[2]), j[0], s16(0x30 + j[1]), j[2], 0xfa, B_BOMB]
    return (None if nobj >= OBJ_MAX else rec), rng


def bomb_step(o, ship, fuel, nobj):
    """One object-walker pass of a Bomb_Fall record o = [x y z vx vy vz life handler].
    Returns (record or None, outcome, fuel after, ship_hit_flag). outcome: 'expire' (life ran out, no burst), 'fly', 'land', 'prox'."""
    x, y, z, vx, vy, vz, life, h = o
    life -= 1
    if life < 0:
        return None, 'expire', fuel, False
    x, y, z = s16(x + vx), s16(y + vy), s16(z + vz)
    gh = S.aground(x, z)
    if s16(gh - y) <= 0x80:
        return None, 'land', fuel, False
    d = man((x, y, z), ship)
    if d <= 0x400:
        f = fuel - 0x333
        crash = f < 0
        return None, 'prox', (0 if crash else f), crash
    return [x, y, z, vx, vy, vz, s16(life), h], 'fly', fuel, False


def plant(x, y, z):
    """`$205f6`: (map cell offset, queue write or None, takes_queue_test) or None when the corner ground blocks it.
    The queue write is conditional on the cell's byte (low five bits 1..3, after bit 5 is set): returned as the value to store."""
    x &= 0xffff; z &= 0xffff
    h2 = S.aground(s16((x & 0xff00) + 0x100), s16((z & 0xff00) + 0x100))
    if h2 > 0x510 or h2 == 0x420:
        return None
    cell = (((x + 0x80) & 0xffff) >> 8) + (((z + 0x80) & 0xffff) & 0xff00)
    return cell, (x, s16(y - 0xb8), z)


def jplant(x, y, z, rng, control=None):
    """`$206b8`: two draws, asr 4 on x then z, then the plant. Returns (plant result, rng, (jx, jz))."""
    rng, d = rng_draw(rng); jx = s16(d) >> (4 if control != 'jit5' else 5)
    rng, d = rng_draw(rng); jz = s16(d) >> 4
    x2, z2 = s16(x + jx), s16(z + jz)
    return plant(x2, y, z2), rng, (x2, z2)


def plants21(pos, rng, control=None):
    """`$2010a`: 21 jittered plants about pos. Returns (list of plant results, rng)."""
    out = []
    for _ in range(21):
        p, rng, _j = jplant(pos[0], pos[1], pos[2], rng, control)
        out.append(p)
    return out, rng


def burst(pos, ship, rng, nobj, control=None):
    """`$2012c` for a bomb at pos. Returns dict: drops 31/51, falling (records appended, in order, before the pool cap), plants (list of
    plant results, one per far drop, None when blocked), nappend, rng, near_at_start."""
    x, y, z = pos
    d = man((x, y, z), ship)
    near = d <= 0x2300
    n = 51 if (not near or nobj <= 0xbb) else 31
    if control == 'always51':
        n = 51
    falling = []; plants = []; pool = nobj - 0     # pool grows by the appended drops; the bomb is removed afterwards
    for _ in range(n):
        dd = man((x, y, z), ship)
        if dd > 0x2300:
            p, rng, (jx, jz) = jplant(x, y, z, rng, control)
            plants.append(p)
        else:
            j = []
            for _k in range(3):
                rng, dv = rng_draw(rng); j.append(s16(dv) >> 10)
            x, y, z = s16(x + j[0]), s16(y + j[1]), s16(z + j[2])
            if pool < OBJ_MAX:
                falling.append([x, y, z, j[0], s16(-0x2a + j[1]), j[2], 0x80, B_DROP]); pool += 1
    return {'drops': n, 'falling': falling, 'plants': plants, 'rng': rng, 'near': near, 'pos': (x, y, z)}
