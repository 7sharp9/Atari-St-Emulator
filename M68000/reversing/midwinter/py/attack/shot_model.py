"""Model of the player's side of combat in the 3D view, transcribed from the routines.

The engagement `$ca7e` (with its box test `$cb2e`) picks the encounter slot that becomes the engaged vehicle `$1cdaa`;
`$1faa6` sets that vehicle's fire odds and `$20cfe` (the tail of its script `$20ce2`) fires its missile; the
player's launchers put the shot object `$1cd7e` in flight; the shot scripts home on the engaged vehicle and set the
kill flag `$14138`; `$141ce` tumbles the vehicle and calls the kill `$cbbe`. The sniping view's hit is a screen pick
(`$14134`, set by the renderer) dispatched by `$14150`.

State (big-endian, absolute addresses):
  $1cd7e  the player's shot (44-byte object, layout in attack_model.py); $1cdaa the engaged vehicle; $1cdd6 the
          aircraft; $1ce02 the bomb/missile/shell. +0 is the object's pick id (-1, -2, -3, -4).
  $25132  rounds per weapon, loaded from the character record +65..+70 by `$3e38` (the copy words between them are
          the HUD's): $25132 (+65) the sniping rifle, $25136 (+66) the ski weapon, $2513a (+67) the glider's,
          $2513e (+68), $25142 (+69), $25146 (+70) the driving modes'
  $14138  the kill flag (1 while the engaged vehicle tumbles); $14134 the object picked under the sniping cross-hair,
          $14136 the sniping shot pending; $141ca the object the sniping explosion sits on
  $1f808  the steering rate (byte offset into the sine table), $1f80a/$1f80c its sine and cosine, $1f80e turn count
  $1f8bc  the radius `$1f884` tests (on both axes)
  $1fb9c..$1fba2  the engaged vehicle's fire words: $1fb9e odds (1 in n a frame), $1fba0 frames before it may fire
          (cleared by every player launch), $1fba2 the last draw
  $2bae0  the engaged slot (-1 none), $2bae2 its unit, $2baec the unit in the window (-1 none), $2bb1e the box
          test's request, $2bb22 the engaged kind
  $2d47e  41 slots of 16 bytes (ai.md section 3): +4/+6 x, y (grid), +8 kind, +12 -1 once engaged, +14 the box latch
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
_root = HERE
while not os.path.exists(os.path.join(_root, 'tools', 'rdis.py')):
    _root = os.path.dirname(_root)
PY = os.path.join(_root, 'reversing', 'midwinter', 'py')
for d in ('army', 'terrain', 'attack'):
    sys.path.insert(0, os.path.join(PY, d))
from army_model import Mem, rand_mod, s16  # noqa: E402,F401
import attack_model as at  # noqa: E402

SHOT, VEH, AIR, PROJ = 0x1cd7e, 0x1cdaa, 0x1cdd6, 0x1ce02
CAMX, CAMY, HEAD, SPEED, TX, TY = 0x12c60, 0x12c64, 0x12c98, 0x15112, 0x19cd4, 0x19cd6
SINE = 0x1c6bc
KILL, PICK, SNIPE, TARGET = 0x14138, 0x14134, 0x14136, 0x141ca
RATE, SINA, COSA, TURNS, RADIUS = 0x1f808, 0x1f80a, 0x1f80c, 0x1f80e, 0x1f8bc
HOLD, ODDS, FIRE_WAIT, DRAW = 0x1fb9c, 0x1fb9e, 0x1fba0, 0x1fba2
ENGAGED, ENG_UNIT, WINDOW, REQ, ENG_KIND = 0x2bae0, 0x2bae2, 0x2baec, 0x2bb1e, 0x2bb22
SLOTS, UNITS, CHAR, RECS = 0x2d47e, 0x2bb96, 0x2c3d6, 0x2b194
VW1, VW2, VW3 = 0x12d6c, 0x12d6e, 0x12d70
AMMO = {'rifle': 0x25132, 'ski': 0x25136, 'glider': 0x2513a, 'drive_b1': 0x2513e, 'drive_b0': 0x25142,
        'drive_space': 0x25146}
M32 = 0xffffffff
BRANCH = {}
CLOBBER = True  # False only in the gate's broken-model control
SNAP = True  # False only in the gate's broken-model control

l, setl, near, move, direction, polar = at.l, at.setl, at.near, at.move, at.direction, at.polar


def hit(name):
    BRANCH[name] = BRANCH.get(name, 0) + 1


def bset(m, a, bit): m.set8(a, m.u8(a) | 1 << bit)
def bclr(m, a, bit): m.set8(a, m.u8(a) & ~(1 << bit))
def w16(v): return v & 0xffff
def neg_flag(v): return bool(v & 0x8000)  # N of a word result (cmp/sub then bpl/bmi)


def sincos(m, head):
    """`$20d9c`: the sine table pair for a heading."""
    a = SINE + (head & 0x3fe)
    return m.w(a), m.w(a + 256)


# ---- launchers -------------------------------------------------------------------------------------------------

def _snd_rifle(m):
    m.set8(0x6a8b, 0xf); bset(m, 0x6a35, 6)


def _snd_ski(m):
    m.setw(0x6a90, 0xa); bset(m, 0x6a35, 7)


def _snd_gun(v):
    def f(m):
        m.setw(0x6a76, v); m.set8(0x6a83, 0xf); m.set8(0x6a85, 0x1f); bset(m, 0x6a35, 5)
    return f


# name: (ammo word, side offset added to the heading, speed added to the player's, height, script, shape pointer,
#        sound, rotation cleared before the speed)
LAUNCHERS = {
    0x1fc6e: (AMMO['ski'], 0x100, 0x12c, 0x28, 0x208d6, 0x31704, _snd_ski),
    0x1fd96: (AMMO['drive_b1'], -0x100, 0xc8, 0x14, 0x20a52, 0x316fc, _snd_gun(0x303)),
    0x1fe56: (AMMO['drive_b0'], 0x100, 0xc8, 0x14, 0x20b0a, 0x316fc, _snd_gun(0x202)),
    0x1ff16: (AMMO['glider'], 0x100, 0xc8, None, 0x20be6, 0x316fc, _snd_gun(0x404)),
    0x1fbbe: (AMMO['drive_space'], 0x100, 0x190, 0, 0x207c4, 0x316f8, _snd_rifle),
}


def launch(m, entry):
    """`$1fc6e` (ski, Space), `$1fd96`/`$1fe56` (driving, mouse buttons 1/0), `$1ff16` (gliding, button 1),
    `$1fbbe` (driving, Space): with a round left, clear the vehicle's fire wait; with the shot object free, spend
    the round and put the shot 50 to the side of the camera (r = 200 through `$145b4`), along the heading."""
    ammo, side, add, height, script, shape, snd = LAUNCHERS[entry]
    if m.w(ammo) == 0:
        hit('no_ammo')
        return
    m.setw(FIRE_WAIT, 0)
    o = SHOT
    if m.sw(o + 38) >= 0:
        hit('shot_busy')
        return
    hit('fire')
    m.setw(ammo, m.w(ammo) - 1)
    snd(m)
    x, y = polar(m, (m.w(HEAD) + side) & 0xffff, 0xc8, l(m, CAMX), l(m, CAMY))
    setl(m, o + 6, x)
    setl(m, o + 10, y)
    for f in (16, 18, 20):
        m.setw(o + f, 0)
    sx, sy = sincos(m, m.w(HEAD))
    m.setw(o + 24, sx)
    m.setw(o + 26, sy)
    m.setw(o + 22, w16(m.w(SPEED) + add))
    m.setw(o + 36, w16(m.w(0x1721c) - m.w(0x12c5e)) if height is None else height)
    m.setw(o + 38, 1)
    setl(m, o + 40, script)
    setl(m, o + 2, l(m, shape))


# ---- steering --------------------------------------------------------------------------------------------------

def rot(d0, d1, d2, d3):
    """`$1f6dc`: (d0, d1) against (d2, d3): D4 = (d0*d3 - d1*d2) >> 14, D3 = (d1*d3 + d0*d2) >> 14, as words."""
    d0, d1, d2, d3 = s16(d0), s16(d1), s16(-d2 & 0xffff), s16(d3)
    d4 = ((d0 * d3 + d1 * d2) << 2) & M32
    e3 = ((d1 * d3 - d0 * d2) << 2) & M32
    return d4 >> 16, e3 >> 16


def far(m, o):
    """`$1f71a`: the object 5000 or more from the camera on either axis (word compare after a low-word abs)."""
    for p, c in ((6, CAMX), (10, CAMY)):
        d = (l(m, o + p) - l(m, c)) & M32
        dw = (-d if d >> 31 else d) & 0xffff
        if not neg_flag(dw - 0x1388):
            return True
    return False


def steer(m, o):
    """`$1f756`: turn the object's direction toward its aim point by at most the rate `$1f808` (snap onto it when
    the remaining angle's sine is below the rate's and the aim is ahead), then step it (`$1f830`)."""
    r = m.w(RATE)
    m.setw(SINA, m.w(SINE + r))
    m.setw(COSA, m.w(SINE + r + 256))
    dx = (l(m, o + 28) - l(m, o + 6)) & M32
    dy = (l(m, o + 32) - l(m, o + 10)) & M32
    if dx == 0 and dy == 0:
        move(m, o)
        return
    d6, d7 = direction(dx, dy)
    d4, d3 = rot(d6, d7, m.w(o + 24), m.w(o + 26))
    if not d3 & 0x8000:
        d2 = (-d4 if d4 & 0x8000 else d4) & 0xffff
        m.setw(TURNS, 0)
        if SNAP and neg_flag(d2 - m.w(SINA)):
            hit('steer_snap')
            m.setw(o + 24, d6)
            m.setw(o + 26, d7)
            move(m, o)
            return
    hit('steer_turn')
    m.setw(TURNS, m.w(TURNS) + 1)
    s = m.w(SINA)
    if not d4 & 0x8000:
        s = -s & 0xffff
    n4, n3 = rot(m.w(o + 24), m.w(o + 26), s, m.w(COSA))
    m.setw(o + 24, n4)
    m.setw(o + 26, n3)
    move(m, o)


def near_r(m, o, r):
    m.setw(RADIUS, r)
    return near(m, o, r)


def _boom(m):
    bset(m, 0x6a34, 4)
    m.setw(0x6a76, 0x1010)
    m.set8(0x6a87, 0xf)


# ---- the shots' scripts (A5 = the shot) ----------------------------------------------------------------------

def ski_shot(m, o=SHOT):
    """`$208d6`, the ski weapon's script: it sinks 4 a frame from 40 and lands (no hit) when its height reaches 0
    exactly; spinning. While the engaged vehicle is active and within 1000 of it on both axes it steers at it
    (rate 8) and kills it within 150; otherwise it flies straight."""
    h = w16(m.w(o + 36) - 4)
    m.setw(o + 36, h)
    if h == 0:
        hit('ski_land')
        m.setw(o + 38, 0)
        bclr(m, 0x6a35, 7); bset(m, 0x6a34, 4); m.setw(0x6a76, 0x808); m.set8(0x6a87, 0xf)
        return
    m.setw(o + 18, w16(m.w(o + 18) + 0x32))
    m.setw(o + 20, w16(m.w(o + 20) + 0x1e))
    if m.sw(VEH + 38) < 0:
        hit('ski_noveh'); move(m, o); return
    setl(m, o + 28, l(m, VEH + 6))
    setl(m, o + 32, l(m, VEH + 10))
    if not near_r(m, o, 0x3e8):
        hit('ski_out'); move(m, o); return
    if near_r(m, o, 0x96):
        hit('ski_kill')
        m.setw(KILL, 1)
        m.setw(o + 38, 0)
        bclr(m, 0x6a35, 7); _boom(m)
        return
    hit('ski_steer')
    m.setw(RATE, 8)
    steer(m, o)


def gun_shot(m, o=SHOT):
    """`$20a52`, the shot of `$1fd96` (driving, mouse button 1): freed beyond 5000 of the camera; accelerates by 200
    a frame to 1600; within 800 of the active engaged vehicle it slows to 500 and steers at it (rate $40), within
    75 it kills it."""
    if far(m, o):
        hit('gun_far'); m.setw(o + 38, 0xffff); return
    if neg_flag(m.w(o + 22) - 0x640):
        m.setw(o + 22, w16(m.w(o + 22) + 0xc8))
    if m.sw(VEH + 38) < 0:
        hit('gun_noveh'); move(m, o); return
    setl(m, o + 28, l(m, VEH + 6))
    setl(m, o + 32, l(m, VEH + 10))
    if not near_r(m, o, 0x320):
        hit('gun_out'); move(m, o); return
    m.setw(o + 22, 0x1f4)
    if near_r(m, o, 0x4b):
        hit('gun_kill')
        m.setw(KILL, 1); m.setw(o + 38, 0)
        bclr(m, 0x6a35, 5); _boom(m)
        return
    hit('gun_steer')
    m.setw(RATE, 0x40)
    steer(m, o)


def rocket(m, o=SHOT):
    """`$207c4`, the shot of `$1fbbe` (driving, Space): freed beyond 5000; its sound fades with distance (`$20882`);
    slows by 100 a frame down to 450; within 2000 of the active engaged vehicle it steers at it (rate $10) and then
    steps a second time, within 100 it kills it."""
    if far(m, o):
        hit('rk_far'); bclr(m, 0x6a35, 6); m.setw(o + 38, 0xffff); return
    ds = []
    for p, c in ((6, CAMX), (10, CAMY)):
        d = (l(m, o + p) - l(m, c)) & M32
        ds.append((-d if d >> 31 else d) & 0xffff)
    d0, d1 = ds
    if not neg_flag(d1 - d0):
        d0 = d1
    d0 = (s16(d0) >> 8) & 0xffff
    v = (0xf - d0) & 0xffff
    if neg_flag(v):
        v = 0
    if v == 0:
        bclr(m, 0x6a35, 6)
    else:
        bset(m, 0x6a35, 6); m.set8(0x6a8b, v)
    if not neg_flag(m.w(o + 22) - 0x1c2):
        m.setw(o + 22, w16(m.w(o + 22) - 0x64))
    if m.sw(VEH + 38) < 0:
        hit('rk_noveh'); move(m, o); return
    setl(m, o + 28, l(m, VEH + 6))
    setl(m, o + 32, l(m, VEH + 10))
    if not near_r(m, o, 0x7d0):
        hit('rk_out'); move(m, o); return
    if near_r(m, o, 0x64):
        hit('rk_kill')
        m.setw(KILL, 1); m.setw(o + 38, 0)
        bclr(m, 0x6a35, 6); _boom(m)
        return
    hit('rk_steer')
    m.setw(RATE, 0x10)
    steer(m, o)
    move(m, o)


SCRIPTS = {0x208d6: ski_shot, 0x20a52: gun_shot, 0x207c4: rocket}


# ---- the kill ----------------------------------------------------------------------------------------------------

def tumble(m):
    """`$141ce`: while the kill flag is set the engaged vehicle tumbles (+18 += $40, +20 += $80 a frame); the call
    that finds +18 at exactly $200 frees it, clears the flag and calls the kill `$cbbe` (then marks nothing engaged).
    Returns True when the model reaches `$cbbe` (the gate stops the game there)."""
    if m.w(KILL) == 0:
        hit('tumble_idle')
        return False
    m.setw(0x1f95e, 0)
    d0, d1 = m.w(VEH + 18), m.w(VEH + 20)
    if d0 == 0x200:
        hit('tumble_kill')
        m.setw(VEH + 38, 0xffff)
        m.setw(KILL, 0)
        return True
    hit('tumble')
    m.setw(VEH + 18, (d0 + 0x40) & 0x3fe)
    m.setw(VEH + 20, (d1 + 0x80) & 0x3fe)
    return False


# ---- sniping -----------------------------------------------------------------------------------------------------

def snipe_hit(m):
    """`$14150`: the object the renderer picked under the cross-hair (`$14134`) after a sniping shot: -2 the engaged
    vehicle (kill flag), -3 the aircraft and -4 the projectile (state 0, destroyed); each gets the explosion
    (`$1fba4`: the shot object runs `$20728`, which `$20d52` calls next)."""
    v = m.w(PICK)
    tgt = {0xfffe: VEH, 0xfffd: AIR, 0xfffc: PROJ}.get(v)
    if tgt is None:
        hit('snipe_none')
        return
    hit(f'snipe_{v - 0x10000}')
    setl(m, TARGET, tgt)
    if tgt == VEH:
        m.setw(KILL, 1)
    else:
        m.setw(tgt + 38, 0)
    m.setw(SHOT + 38, 1)
    setl(m, SHOT + 40, 0x20728)


def explosion(m):
    """`$20728`: the shot object put on the target `$141ca` for one frame, with the explosion sound."""
    a4 = l(m, TARGET)
    bset(m, 0x6a34, 4); bclr(m, 0x6a34, 5)
    m.setw(0x6a76, 0x1010); m.set8(0x6a87, 0xf)
    m.setw(SHOT + 38, 0)
    setl(m, SHOT + 6, l(m, a4 + 6))
    setl(m, SHOT + 10, l(m, a4 + 10))
    m.setw(SHOT + 36, m.w(a4 + 36))


# ---- the engagement ------------------------------------------------------------------------------------------

def to_grid(m, x, y):
    """`$1d074`: world (long) to slot grid (word)."""
    d0 = (s32(x) >> 8) & 0xffff
    d1 = (s32(y) >> 8) & 0xffff
    d0 = (d0 - 1 - 0x64) & 0xffff
    d1 = (-(d1 - 1 - 0x64)) & 0xffff
    d0 = (d0 + 2 * m.w(TX)) & 0xffff
    d1 = (d1 + 2 * m.w(TY)) & 0xffff
    return d0, d1


def from_grid(m, gx, gy):
    """`$1d048`: slot grid to world (long)."""
    d2 = (gx >> 1) & 0xffff
    d3 = (gy >> 1) & 0xffff
    d2 = (d2 - m.w(TX)) & 0xffff
    d3 = (-(d3 - m.w(TY))) & 0xffff
    d2 = (2 * ((d2 + 0x32) & 0xffff) + 1) & 0xffff
    d3 = (2 * ((d3 + 0x32) & 0xffff) + 1) & 0xffff
    return (s16(d2) * 0x100) & M32, (s16(d3) * 0x100) & M32


def s32(v):
    v &= M32
    return v - (1 << 32) if v >> 31 else v


def engage(m, box=0x20):
    """`$ca7e` with `$cb2e`: slots 40 down to 0, active and not engaged before, are tested against the 32 x 32 box
    [g - 16, g + 16) around the camera's grid cell g. A slot inside whose latch +14 is clear sets the latch and
    requests; one outside clears its latch. A request with nothing engaged engages that slot: `$2bae0`, its unit,
    its kind, the vehicle object's shape `$316e4[kind]` and its position. So the highest-numbered slot entering
    the box is engaged, a slot is engaged once only (+12), and one that was in the box when another was engaged
    must leave it and come back. After an engagement the box's x origin register holds the engaged kind * 4, so
    the lower-numbered slots are tested against that on x (in practice outside, which clears their latches)."""
    if m.sw(WINDOW) < 0:
        hit('eng_nowindow')
        return
    gx, gy = to_grid(m, l(m, CAMX), l(m, CAMY))
    gx, gy = (gx - 0x10) & 0xffff, (gy - 0x10) & 0xffff
    for i in range(40, -1, -1):
        s = SLOTS + 16 * i
        if m.u8(s) & 0x80 or m.sw(s + 12) < 0:
            continue
        m.setw(REQ, 0)
        d6 = m.sw(s + 14)
        d3 = (m.w(s + 4) - gx) & 0xffff
        d4 = (m.w(s + 6) - gy) & 0xffff
        if d3 & 0x8000 or d4 & 0x8000 or d3 >= box or d4 >= box:
            m.setw(s + 14, 0)
            continue
        if d6 >= 0:
            m.setw(REQ, 0xffff)
            m.setw(s + 14, 0xffff)
        if m.w(REQ) == 0:
            hit('eng_latched')
            continue
        if m.sw(ENGAGED) >= 0:
            hit('eng_busy')
            continue
        hit('engage')
        m.setw(ENGAGED, i)
        m.setw(ENG_UNIT, m.w(WINDOW))
        k = m.w(s + 8)
        m.setw(ENG_KIND, k)
        setl(m, VEH + 2, l(m, 0x316e4 + s16((k << 2) & 0xffff)))
        m.setw(s + 12, 0xffff)
        x, y = from_grid(m, m.w(s + 4), m.w(s + 6))
        setl(m, VEH + 6, x)
        setl(m, VEH + 10, y)
        if CLOBBER:
            gx = (k << 2) & 0xffff  # D0 now holds the shape index: the lower slots are boxed against it on x


# ---- the engaged vehicle's fire --------------------------------------------------------------------------------

def veh_odds(m):
    """`$1faa6` (on each new engagement, from `$1fa0a`): the engaged vehicle's missile odds `$1fb9e` (1 in n a frame)
    and its first wait `$1fba0`, from the character's byte +72 (c), the unit's byte +12 and the vehicle record's
    words $12d6c/$12d6e/$12d70:
        q = $12d6c / (unit+12 + 1);  n = (((rand mod q) + c) >> 1 + $12d6e + c) >> 2;  wait = ($12d70 * c + 100) >> 2
    then by kind: the command vehicle n = 5, wait 30; a bull or tanker n += 10000 (never in practice); a wolf +5, a
    cat +10, a fox +15; and 1 time in 11 the wait is 10."""
    c = m.u8(RECS + m.w(CHAR) * 0x4a + 72)
    u = m.u8(UNITS + ((m.w(ENG_UNIT) << 4) & 0xffff) + 12) + 1
    d1 = s32(m.sw(VW1)) & M32
    q = d1 // u
    if q > 0xffff:
        hit('odds_overflow')
        q = d1
    else:
        q = ((d1 % u) << 16) | q
    m.setw(DRAW, q & 0xffff)
    d0 = rand_mod(m, q & 0xffff)
    d0 = s16((d0 + c) & 0xffff) >> 1
    d0 = (d0 + m.w(VW2) + c) & 0xffff
    m.setw(ODDS, (s16(d0) >> 2) & 0xffff)
    d0 = (m.w(VW3) * c) & M32
    d0 = (d0 + 0x64) & 0xffff
    m.setw(FIRE_WAIT, (s16(d0) >> 2) & 0xffff)
    m.setw(HOLD, 0)
    k = m.sw(SLOTS + ((m.w(ENGAGED) << 4) & 0xffff) + 8)
    if k < 0:
        hit('odds_cmd')
        m.setw(FIRE_WAIT, 0x1e)
        m.setw(ODDS, 5)
    else:
        m.setw(ODDS, m.w(ODDS) + {0: 0x2710, 1: 0x2710, 2: 5, 3: 0xa}.get(k, 0xf) & 0xffff)
    if rand_mod(m, 0xb) == 0:
        hit('odds_wait10')
        m.setw(FIRE_WAIT, 0xa)


def veh_fire(m, a5=VEH):
    """`$20cfe..$20d2c`, the tail of the engaged vehicle's script `$20ce2`: while the wait `$1fba0` runs it counts
    down; then each frame `rand mod $1fb9e` is drawn and a 0 fires the missile `$201e0`."""
    if m.w(FIRE_WAIT):
        hit('vf_wait')
        m.setw(FIRE_WAIT, m.w(FIRE_WAIT) - 1)
        return
    d0 = rand_mod(m, m.w(ODDS))
    m.setw(DRAW, d0)
    if d0 == 0:
        hit('vf_fire')
        at.missile(m, a5)
    else:
        hit('vf_hold')
