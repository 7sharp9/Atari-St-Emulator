"""Model of the encounter: the search `$c2f0` and the per-frame spawn and move `$c4f2` (ai.md section 3), transcribed
from the routines.

State (big-endian, absolute addresses):
  $19cd4/$19cd6  terrain target (the player's cell); the encounter window is [2*(t-50), 2*(t-50)+200) on each axis,
                 kept in $2bb06/$2bb08
  $2baec  the unit in the window (-1 none); $2baee/$2baf0 its x, y; $2baf6/$2baf8 its target node's x, y (-1 none)
  $2bb0a..$2bb12  working copies of the unit's +6..+10 (Snow bull, Tanker, Snow wolf, Snow cat, Snow fox counts);
                 $2bb14 = bulls + tankers, $2bb16 = wolves + cats + foxes still to place
  $2bb2c  1 when the unit's +5 bit 6 is clear (the unit shows its own object in slot 0)
  $2d47e  41 object slots of 16 bytes: +0 a long script pointer (bulls, tankers) or a word direction 0..3 (wolves,
          cats, foxes; a negative word or long -1 = free); +4/+6 x, y; +8 category 0..4; +10 1 = follows the script,
          -1 = wanders; +12 -1 once engaged; +14 near-player latch
  $2d70e  the script: one direction byte per step from the unit to its target node, $ff at the end (`$c730`)
  $3ddb4  100 x 100 byte grid of the window, nonzero = blocked (read only)
  $2bae0  the engaged slot (-1 none); $d57c objects still allowed in view; $2bb1a/$2bb1c spawn countdown (5 frames)
Directions: 0 = y-1, 1 = x+1, 2 = y+1, 3 = x-1.
"""
from army_model import Mem, UNITS, NODES, rand_d598, rand_mod, s16  # noqa: F401

SLOTS, SCRIPT, GRID = 0x2d47e, 0x2d70e, 0x3ddb4
TX, TY, WX, WY = 0x19cd4, 0x19cd6, 0x2bb06, 0x2bb08
ENC, EX, EY, PX, PY, NX, NY = 0x2baec, 0x2baee, 0x2baf0, 0x2baf2, 0x2baf4, 0x2baf6, 0x2baf8
CNT = [0x2bb0a, 0x2bb0c, 0x2bb0e, 0x2bb10, 0x2bb12]
SUMA, SUMB, OWN, ENGAGED, ENGUNIT, ROOM = 0x2bb14, 0x2bb16, 0x2bb2c, 0x2bae0, 0x2bae2, 0xd57c
KIND = ['Snow bull', 'Tanker', 'Snow wolf', 'Snow cat', 'Snow fox']  # $316e4 = $31698 + 4 * $13: types $13..$17
STEP = {0: (0, -1), 1: (1, 0), 2: (0, 1)}
BRANCH = {}


def hit(name):
    BRANCH[name] = BRANCH.get(name, 0) + 1


def step(d):
    return STEP.get(d, (-1, 0))  # `$c960`: 0, 1, 2, anything else is x-1


def blocked(m, x, y):
    """`$c854`/`$ca00`: None when (x, y) is outside the window, else the grid byte."""
    dx, dy = (x - m.w(WX)) & 0xffff, (y - m.w(WY)) & 0xffff
    if dx & 0x8000 or dy & 0x8000 or dx >= 200 or dy >= 200:
        return None
    return m.u8(GRID + (dy >> 1) * 100 + (dx >> 1))


def clear_slot(m, i):
    """`$cd9e`."""
    a = SLOTS + 16 * i
    m.b[a:a + 4] = b'\xff\xff\xff\xff'
    m.b[a + 4:a + 16] = bytes(12)


def search(m):
    """`$c2f0`."""
    wx, wy = s16((m.w(TX) - 50) * 2), s16((m.w(TY) - 50) * 2)
    m.setw(WX, wx); m.setw(WY, wy)
    for u in range(31, -1, -1):
        a = UNITS + 16 * u
        if not m.u8(a + 4) & 0x80:
            continue
        dx, dy = (m.w(a) - wx) & 0xffff, (m.w(a + 2) - wy) & 0xffff
        if dx & 0x8000 or dy & 0x8000 or dx >= 200 or dy >= 200:
            continue
        break
    else:
        hit('none in window')
        m.setw(ENC, 0xffff)
        return
    hit('found')
    m.setw(ENC, u)
    m.setw(OWN, 0 if m.u8(a + 5) & 0x40 else 1)
    m.setw(EX, m.w(a)); m.setw(EY, m.w(a + 2))
    t = m.u8(a + 13)
    if t == 0 or t & 0x80:
        m.setw(NX, 0xffff); m.setw(NY, 0xffff)
    else:
        m.setw(NX, m.w(NODES + 4 * t)); m.setw(NY, m.w(NODES + 4 * t + 2))
    for i in range(5):
        m.setw(CNT[i], m.u8(a + 6 + i))
    m.setw(SUMA, m.u8(a + 6) + m.u8(a + 7))
    m.setw(SUMB, m.u8(a + 8) + m.u8(a + 9) + m.u8(a + 10))
    eng = m.sw(ENGAGED)
    for i in range(40, -1, -1):  # `$d026`
        if i != eng:
            clear_slot(m, i)
    if eng > 0:
        m.setw(SLOTS + 16 * eng, rand_d598(m) & 3)
        m.setw(SLOTS + 16 * eng + 10, 0xffff)
    if m.w(OWN):
        m.setw(SLOTS + 2, m.w(OWN)); m.setw(SLOTS, 0)
        if m.w(ENGAGED):
            m.setw(SLOTS + 4, m.w(EX)); m.setw(SLOTS + 6, m.w(EY))
            for o in (10, 8, 14):
                m.setw(SLOTS + o, 0xffff)
    m.b[0x2bad4:0x2bad8] = SCRIPT.to_bytes(4, 'big')
    for a, v in ((0x2bb1c, 5), (0x2bb1a, 5), (0x2bafa, 5), (0x2bb00, 0), (ROOM, 0x26)):
        m.setw(a, v)
    if eng < 0:
        m.setw(ROOM, 0x27); m.setw(ENGAGED, 0xffff); m.setw(ENGUNIT, 0xffff)
    if m.sw(NX) >= 0:
        m.setw(PX, m.w(EX)); m.setw(PY, m.w(EY))
        path(m)


def path(m):
    """`$c730`: the script from the unit to its target node, a randomised walk around blocked cells."""
    hit('path')
    p, d = SCRIPT, 0
    m.setw(0x2bafe, 1)
    for a in (0x2bb02, 0x2bb04, 0x2bb34):
        m.setw(a, 0)
    for _ in range(20000):
        if m.sw(0x2bb34) >= 0:  # `$c7fe`: x or y in proportion to the distance left
            ax, ay = s16(m.w(NX) - m.w(PX)), s16(m.w(NY) - m.w(PY))
            r = s16(rand_mod(m, (abs(ax) + abs(ay)) & 0xffff))
            d = (3 if ax < 0 else 1) if r < abs(ax) else (0 if ay < 0 else 2)
        else:  # following a wall: try turning back left first
            d = (d - 1) & 3
        first = True
        while True:  # `$c770`/`$c796`: turn right until a free cell
            sx, sy = step(d)
            g = blocked(m, (m.w(PX) + sx) & 0xffff, (m.w(PY) + sy) & 0xffff)
            if g is None:
                m.setw(0x2bb32, 0xffff)
                return end(m, p)
            m.setw(0x2bb32, 1 if g else 0)
            if not g:
                if first:
                    m.setw(0x2bb34, 0)
                break
            if first:
                m.setw(0x2bb34, 0xffff)
                hit('wall')
            first = False
            d = (d + 1) & 3
        m.set8(p, d); p += 1  # `$c8d8`
        sx, sy = step(d)
        m.setw(PX, m.w(PX) + sx); m.setw(PY, m.w(PY) + sy)
        if m.w(PX) == m.w(NX):
            m.setw(0x2bb02, 0xffff)
        if m.w(PY) == m.w(NY):
            m.setw(0x2bb04, 0xffff)
        if m.w(0x2bb02) & m.w(0x2bb04):
            hit('path reached target')
            return end(m, p)
    raise RuntimeError('path did not end')


def end(m, p):
    m.setw(0x2bb00, 0xffff)
    m.set8(p, 0xff)


def frame(m):
    """`$c4f2`: every fifth frame place one object, chosen in proportion to the counts left; then move every slot."""
    u = m.sw(ENC)
    if u < 0 or not m.u8(UNITS + 16 * u + 4) & 0x80:
        hit('no encounter')
        return
    if m.w(ROOM) and spawn_due(m):
        spawn(m)
    eng = m.sw(ENGAGED)
    for i in range(40, -1, -1):
        if i == eng:
            continue
        a = SLOTS + 16 * i
        if m.w(a + 10) & 0x8000:
            if i or m.w(SLOTS + 2):
                turn(m, i)
                walk(m, i)
        elif m.sw(NX) >= 0:
            follow(m, i)


def spawn_due(m):
    m.setw(0x2bb1a, m.w(0x2bb1a) - 1)
    if m.w(0x2bb1a):
        return False
    m.setw(0x2bb1a, m.w(0x2bb1c))
    return True


def spawn(m):
    """`$c52e..$c6e4`."""
    total = sum(m.w(a) for a in CNT) & 0xffff
    if total == 0:  # `divu` by zero: the vector is a bare `rte`, so D0 keeps rand & $ffff and its swapped half is 0
        hit('spawn: zero divide')
        rand_d598(m)
        r = 0
    else:
        r = rand_mod(m, total)
    m.setw(0x2bb18, 1)
    cat = None
    for c in range(5):
        r = s16(r - m.w(CNT[c]))
        if r >= 0:
            continue
        if m.w(CNT[c]) == 0:
            hit('spawn: empty category')
            return
        if c < 2 and m.sw(NX) < 0:
            if c == 0:
                hit('spawn: bull with no target')
                return
            continue  # a tanker with no target falls through to the wolf test with the same r
        m.setw(CNT[c], m.w(CNT[c]) - 1)
        m.setw(0x2bb20, c)
        if c >= 2:
            m.setw(0x2bb18, 0xffff)
        cat = c
        break
    if cat is None:
        hit('spawn: r not placed')  # unreachable while r < total; the game then places with the old $2bb20
    for i in range(1, 41):
        if m.b[SLOTS + 16 * i:SLOTS + 16 * i + 4] == b'\xff\xff\xff\xff':
            break
    else:
        hit('spawn: no free slot')
        return
    a = SLOTS + 16 * i
    if m.w(0x2bb18) & 0x8000:
        if m.w(SUMB) == 0:
            hit('spawn: wanderers exhausted')
            return
        m.setw(SUMB, m.w(SUMB) - 1)
        m.setw(a, rand_d598(m) & 3)
    else:
        if m.w(SUMA) == 0:
            hit('spawn: script objects exhausted')
            return
        m.setw(SUMA, m.w(SUMA) - 1)
        m.b[a:a + 4] = SCRIPT.to_bytes(4, 'big')
    hit(f'spawn {KIND[m.w(0x2bb20)]}')
    m.setw(a + 4, m.w(EX)); m.setw(a + 6, m.w(EY))
    m.setw(a + 8, m.w(0x2bb20)); m.setw(a + 10, m.w(0x2bb18))
    m.setw(a + 12, 0); m.setw(a + 14, 0xffff)
    m.setw(ROOM, m.w(ROOM) - 1)


def follow(m, i):
    """`$c922`: one script step; at the script's end restart from the unit, or wander once engaged."""
    a = SLOTS + 16 * i
    p = int.from_bytes(m.b[a:a + 4], 'big')
    if p == 0xffffffff:
        return
    d = m.u8(p & 0xffffff)
    if d & 0x80:
        if m.w(a + 12) & 0x8000:
            hit('script end: wander')
            m.setw(a, rand_d598(m) & 3)
            m.setw(a + 10, 0xffff)
        else:
            hit('script end: restart')
            m.b[a:a + 4] = SCRIPT.to_bytes(4, 'big')
            m.setw(a + 4, m.w(EX)); m.setw(a + 6, m.w(EY))
            m.setw(a + 14, 0xffff)
        return
    m.b[a:a + 4] = (p + 1).to_bytes(4, 'big')
    sx, sy = step(d)
    m.setw(a + 4, m.w(a + 4) + sx); m.setw(a + 6, m.w(a + 6) + sy)


def turn(m, i):
    """`$c9c6`: with chance 1/16 turn right."""
    a = SLOTS + 16 * i
    d = m.w(a)
    if d & 0x8000:
        return
    r = rand_d598(m) & 0xf
    if r < 2:
        m.setw(a, (d + r) & 3)


def walk(m, i):
    """`$ca00`: one step unless it leaves the window or enters a blocked cell."""
    a = SLOTS + 16 * i
    d = m.w(a)
    if d & 0x8000:
        return
    sx, sy = step(d)
    x, y = (m.w(a + 4) + sx) & 0xffff, (m.w(a + 6) + sy) & 0xffff
    if blocked(m, x, y) == 0:
        m.setw(a + 4, x); m.setw(a + 6, y)


# The kill: `$cbbe` runs when the engaged object `$2bae0` (of unit `$2bae2`) is destroyed.
DEAD_UNITS, LIVE_UNITS, DEAD_VEH, LIVE_VEH = 0x2bad8, 0x2bada, 0x2badc, 0x2bade
TALLY, NOSUM = 0x2c11e, 0xd57a
DOUBLE_COST = 3  # categories from here on (Snow cat, Snow fox) cost the unit 2 strength
CASCADE = True  # the gate's control turns the leader cascade off


def add(m, a, v):
    m.setw(a, m.w(a) + v)


def kill(m):
    """`$cbbe` up to its radio message `$d048` (an interrupt wait, so the gate stops there). Returns 'message' when it
    reaches `$cd6e`, 'return' otherwise."""
    m.setw(0x2bb24, 0xffff)
    e = m.sw(ENGAGED)
    if e < 0:
        return tail(m)
    for a in (0x2c11a, 0x2c11c, 0x2c122, NOSUM):
        m.setw(a, 0)
    cat = m.w(SLOTS + 16 * e + 8)
    u = m.w(ENGUNIT)
    a = UNITS + 16 * u
    clear_slot(m, e)
    m.setw(0x2bb26, 0xffff)
    if e:
        hit('kill: vehicle')
        m.setw(0x2bb26, 0)
        cost = 2 if cat >= DOUBLE_COST else 1
        add(m, LIVE_VEH, -1); add(m, DEAD_VEH, 1)
        if not m.u8(a + 4) & 0x80:
            return tail(m)
        m.set8(a + 6 + cat, m.u8(a + 6 + cat) - 1)
        add(m, ROOM, 1)
        for _ in range(cost):
            m.set8(a + 14, m.u8(a + 14) - 1)
            if m.u8(a + 14) == 0:
                break
        else:
            return tail(m)
    hit('kill: unit')
    g = m.u8(a + 15)
    unit_dead(m, u)
    if m.w(0x2bb26):
        add(m, TALLY, -1)
    m.setw(0x2c12e, m.w(0x2c118))
    m.setw(0x2c11a, m.w(TALLY))
    if g == 0xff:
        return tail(m, unit_gone=True)
    g &= 0x7f
    if g & 8:
        hit('kill: member')
        return 'message'
    hit('kill: leader')
    m.setw(0x2c124, m.w(0x2c116))
    m.b[0x2c126:0x2c12e] = b'\xff' * 8
    m.setw(0x2c120, m.w(0x2c132 + 2 * m.w(0x2c116)))
    m.setw(0x2c11a, 0)
    m.setw(0x2c11c, m.w(TALLY))
    m.setw(0x2c122, 0xffff)
    p = 0x2c126
    for v in range(31, -1, -1) if CASCADE else ():
        b = UNITS + 16 * v
        k = m.u8(b + 15)
        if k != 0xff:
            if k & 0x80:
                m.setw(NOSUM, 0xffff)
            k &= 0x7f
            if k & 8 and (k & ~8) == g:
                hit('kill: cascade')
                was = m.u8(b + 4)
                unit_dead(m, v)
                d1 = m.w(0x2c118) | (0 if was & 0x80 else 0x8000)
                m.setw(p, d1); p += 2
                add(m, 0x2c11c, m.w(TALLY))
        m.setw(NOSUM, 0)
    return 'message'


def unit_dead(m, u):
    """`$cdd0`: the unit and its remaining vehicles are written off."""
    a = UNITS + 16 * u
    m.setw(TALLY, 0)
    m.setw(0x2bb24, u)  # `$ce8c`
    m.setw(0x2c118, 0xffff); m.setw(0x2c116, 0xffff)
    k = m.u8(a + 15)
    if k != 0xff:
        m.setw(0x2c118 if k & 8 else 0x2c116, m.u8(a + 5) & 0x3f)
    if u == m.w(ENC):
        for i in range(40, -1, -1):
            clear_slot(m, i)
    m.set8(a + 4, m.u8(a + 4) & 0x7f)
    if not m.u8(a + 5) & 0x40:
        add(m, TALLY, 1)
        m.set8(a + 5, m.u8(a + 5) | 0x40)
        add(m, LIVE_VEH, -1); add(m, DEAD_VEH, 1)
    m.set8(a + 14, 0)
    m.set8(a + 15, m.u8(a + 15) | 0x80)
    n = sum(m.u8(a + 6 + i) for i in range(5))
    m.b[a + 6:a + 11] = bytes(5)
    if not m.w(NOSUM) & 0x8000:
        add(m, TALLY, n); add(m, LIVE_VEH, -n); add(m, DEAD_VEH, n)
        add(m, LIVE_UNITS, -1); add(m, DEAD_UNITS, 1)


def tail(m, unit_gone=False):
    """`$cd72` (after a kill with no group: the encounter ends if it was this unit), then `$cd88`."""
    if unit_gone and m.w(ENGUNIT) == m.w(ENC):
        m.setw(ENC, 0xffff)
    m.setw(ENGAGED, 0xffff); m.setw(ENGUNIT, 0xffff)
    return 'return'
