"""Model of the attacks on the player in the 3D view (ai.md section 4), transcribed from the routines.

State (big-endian, absolute addresses):
  $2c17c, $2c17e, $2c180  the options' BOMBERS, MORTARS and TRAINING words (-1 on, 0 off; `$10986..$10996` flip them)
  $1fa08  the vehicle's attack mask, written by its setup routine: bit 0 bombers, bit 1 mortars, bit 2 missiles
  $1cd7e  four 44-byte objects run by `$20d52`: $1cd7e the player's shot, $1cdaa the engaged encounter vehicle,
          $1cdd6 the bomber or mortar, $1ce02 a bomb, missile or mortar shell. +2 shape (long), +6/+10 x, y (long),
          +16/+18/+20 rotation, +22 speed, +24/+26 direction (sine units), +28/+32 aim point (long), +36 height,
          +38 state (-1 free, 1 running, 0 done), +40 script (long)
  $12c60/$12c64  camera x, y (long); $12c98 heading (0..$3fe, even); $19cd4/$19cd6 the terrain target
  $20e4c, $20e4a  the bomber's and the mortar's launch odds (1 in n per frame, -1 = draw new odds); $20e48 the odds
          `$20db4` drew; $20d94/$20d96 copies; $20e42/$20e44/$20d98 its working words
  $200e0..$200e4  shared attack words; $14dfc set to 1 by a hit (the 3D loop then ends the trip)
  $1c6bc  sine table, 512 words (cosine 128 words on)
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'army'))
sys.path.insert(0, os.path.join(HERE, '..', 'terrain'))
from army_model import Mem, rand_mod, s16  # noqa: E402
from terrain_gen import isqrt_198d8  # noqa: E402

BOMBERS, MORTARS, TRAINING, MASK = 0x2c17c, 0x2c17e, 0x2c180, 0x1fa08
OBJS, SHOT, ENGAGED, BOMBER, SHELL = 0x1cd7e, 0x1cd7e, 0x1cdaa, 0x1cdd6, 0x1ce02
CAMX, CAMY, HEAD, TX, TY = 0x12c60, 0x12c64, 0x12c98, 0x19cd4, 0x19cd6
ODDS_B, ODDS_M, DRAWN, COPY_B, COPY_M = 0x20e4c, 0x20e4a, 0x20e48, 0x20d94, 0x20d96
Q, Q8, RATE = 0x20e42, 0x20e44, 0x20d98
A0E0, A0E2, A0E4 = 0x200e0, 0x200e2, 0x200e4
HIT, FALL, SINE = 0x14dfc, 0x20a50, 0x1c6bc
CHAR, RECS, DIVISOR = 0x2c3d6, 0x2b194, 0x12d72
CENTRE = (0xa80, 0xa38)  # the terrain point the odds are measured from
BRANCH = {}
M32 = 0xffffffff


def hit(name):
    BRANCH[name] = BRANCH.get(name, 0) + 1


def l(m, a): return int.from_bytes(m.b[a:a + 4], 'big')
def setl(m, a, v): m.b[a:a + 4] = (v & M32).to_bytes(4, 'big')
def s32(v): v &= M32; return v - (1 << 32) if v >> 31 else v


def polar(m, head, r, x, y):
    """`$145b4`: (x + (sin * r) >> 16, y + (cos * r) >> 16), sine table at $1c6bc."""
    a = SINE + (head & 0x3fe)
    sx, sy = m.sw(a), m.sw(a + 256)
    return (x + ((sx * r) >> 16)) & M32, (y + ((sy * r) >> 16)) & M32


def divs(n, d):
    """68000 divs.w: (quotient, overflow); the quotient truncates toward 0."""
    q = abs(n) // abs(d)
    q = q if (n < 0) == (d < 0) else -q
    return q, not -0x8000 <= q <= 0x7fff


def direction(dx, dy):
    """`$1f6f8`: (dx, dy) * 2^14 / |(dx, dy)| on the low words."""
    dx, dy = s16(dx), s16(dy)
    root = s16(isqrt_198d8(dx * dx + dy * dy))
    out = []
    for v in (dx, dy):
        n = s32(v << 14)
        q, ovf = divs(n, root)
        out.append((n if ovf else q) & 0xffff)
    return out


def near(m, o, r):
    """`$1f884`: aim point within r of the object on both axes (each |d| taken on the low word, signed compare)."""
    for a, b in ((28, 6), (32, 10)):
        d = (l(m, o + a) - l(m, o + b)) & M32
        dw = (-d if d >> 31 else d) & 0xffff
        if s16(dw - r) >= 0:
            return False
    return True


def move(m, o):
    """`$1f830`: x += (dir * speed) >> 16 on each axis."""
    sp = m.sw(o + 22)
    for d, p in ((24, 6), (26, 10)):
        setl(m, o + p, l(m, o + p) + ((m.sw(o + d) * sp) >> 16))


def odds(m):
    """`$20db4`: the launch odds from the distance to CENTRE, the character's byte +72 and the vehicle's divisor."""
    r = m.u8(RECS + m.w(CHAR) * 0x4a + 72)
    m.setw(RATE, r)
    dx, dy = s16(m.w(TX) - CENTRE[0]), s16(m.w(TY) - CENTRE[1])
    d1 = ((dx * dx + dy * dy) << 1) & M32
    d1 = (d1 >> 16) * (r + 50)
    q = d1 // m.w(DIVISOR)
    if q > 0xffff:
        hit('odds_overflow')
        q = d1  # divu overflow leaves the register unchanged
    q &= 0xffff
    m.setw(Q, q)
    m.setw(Q8, s16(q) >> 3)
    d0 = rand_mod(m, (q + 50) & 0xffff)
    d0 = (d0 + m.w(Q8) + 20) & 0xffff
    if d0 & 0x8000:
        d0 = 0x7d00
    m.setw(DRAWN, d0)


def launch(m, flag, bit, oddsw, copy, shape, speed2, height4, script):
    """`$1ffe0` (bomber) and `$200e8` (mortar): one chance a frame to send the attacker at the player."""
    if m.w(flag) == 0 or not m.u8(MASK) >> bit & 1:
        hit('off')
        return
    o = BOMBER
    if m.sw(o + 38) >= 0:
        hit('busy')
        return
    if m.sw(oddsw) < 0:
        odds(m)
        m.setw(oddsw, m.w(DRAWN))
        m.setw(copy, m.w(DRAWN))
    if rand_mod(m, m.w(oddsw)) != 0:
        hit('wait')
        return
    hit('launch')
    m.setw(oddsw, 0xffff)
    if bit == 0:
        m.setw(A0E0, 6)
    m.setw(A0E2, speed2)
    m.setw(A0E4, height4)
    setl(m, o + 2, l(m, shape))
    x, y = polar(m, m.w(HEAD), 0x4650, l(m, CAMX), l(m, CAMY))
    setl(m, o + 6, x)
    setl(m, o + 10, y)
    for f in (16, 18, 20):
        m.setw(o + f, 0)
    m.setw(o + 22, 0x190)
    setl(m, o + 28, l(m, CAMX))
    setl(m, o + 32, l(m, CAMY))
    m.setw(o + 36, 0xc8)
    m.setw(o + 38, 1)
    setl(m, o + 40, script)
    dx, dy = direction(l(m, o + 28) - l(m, o + 6), l(m, o + 32) - l(m, o + 10))
    m.setw(o + 24, dx)
    m.setw(o + 26, dy)


def bomber(m):
    launch(m, BOMBERS, 0, ODDS_B, COPY_B, 0x3170c, 0x1964, 0xc8, 0x2040e)


def mortar(m):
    launch(m, MORTARS, 1, ODDS_M, COPY_M, 0x31700, 0xbb8, 0xfa, 0x20524)


def missile(m, a5):
    """`$201e0`, called by the engaged vehicle's script `$20ce2` with A5 = that vehicle: unless TRAINING is on, fire
    a missile from it. The aim direction `$1f6f8` computes is overwritten with the vehicle's own heading, and
    `$1f830` then steps the vehicle (A5), not the missile."""
    if m.w(TRAINING) != 0 or not m.u8(MASK) >> 2 & 1:
        hit('missile_off')
        return
    o = SHELL
    if m.sw(o + 38) >= 0:
        hit('missile_busy')
        return
    hit('missile')
    m.setw(A0E2, 0x1770)
    m.setw(A0E4, 0x46)
    setl(m, o + 2, l(m, 0x316fc))
    setl(m, o + 6, l(m, a5 + 6))
    setl(m, o + 10, l(m, a5 + 10))
    x, y = polar(m, m.w(HEAD), 0x1770, l(m, CAMX), l(m, CAMY))
    setl(m, o + 28, x)
    setl(m, o + 32, y)
    for f in (16, 18, 20):
        m.setw(o + f, 0)
    m.setw(o + 22, 0x258)
    m.setw(o + 36, 0xa)
    m.setw(0x206ea, 0xa)
    m.setw(0x206ec, 0)
    m.setw(o + 38, 1)
    setl(m, o + 40, 0x20594)
    m.setw(o + 24, m.w(a5 + 24))
    m.setw(o + 26, m.w(a5 + 26))
    move(m, a5)
    m.set8(0x6aaf, 0x14)
    m.set8(0x6a34, m.u8(0x6a34) | 8)


def boom(m):
    """The landing sound both hit tests start (`$6a35` bit 7 off, `$6a34` bit 4 on, `$6a76`, `$6a87`)."""
    m.set8(0x6a35, m.u8(0x6a35) & 0x7f)
    m.set8(0x6a34, m.u8(0x6a34) | 0x10)
    m.setw(0x6a76, 0x808)
    m.set8(0x6a87, 0xf)


def bomb(m):
    """`$209a0`, the bomb's script (A5 = $1ce02): it falls faster each frame; on landing it hits when it is within
    200 of the point 180 ahead of the camera on both axes."""
    o = SHELL
    m.setw(o + 20, (m.w(o + 20) + 0x32) & 0x3fe)
    v = (m.w(FALL) + 12) & 0xffff
    m.setw(FALL, v)
    h = s16(m.w(o + 36) - v)
    m.setw(o + 36, h)
    if h >= 0:
        hit('falling')
        move(m, o)
        return
    m.setw(o + 36, 0)
    m.setw(o + 38, 0)
    x, y = polar(m, m.w(HEAD), 0xb4, l(m, CAMX), l(m, CAMY))
    setl(m, o + 28, x)
    setl(m, o + 32, y)
    m.setw(0x1f8bc, 0xc8)
    if near(m, o, 0xc8):
        hit('bomb_hit')
        m.setw(HIT, 1)
    else:
        hit('bomb_miss')
    boom(m)


def shell(m):
    """`$20776`, a mortar shell's script: it lands at once and hits when within 200 of the camera on both axes."""
    o = SHELL
    m.set8(0x6a34, m.u8(0x6a34) | 0x10)
    m.setw(0x6a76, 0x1010)
    m.set8(0x6a87, 0xf)
    m.setw(o + 38, 0)
    setl(m, o + 28, l(m, CAMX))
    setl(m, o + 32, l(m, CAMY))
    m.setw(0x1f8bc, 0xc8)
    if near(m, o, 0xc8):
        hit('shell_hit')
        m.setw(HIT, 1)
    else:
        hit('shell_miss')
