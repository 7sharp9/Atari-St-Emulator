"""Model of sabotage (the PLANT EXPLOSIVES screen `$3f98`), transcribed from the routines.

State (big-endian, absolute addresses; A6 = $2c376):
  $2b194  32 character records of $4a bytes: +1 Morale (the live copy is $2553c), +6 Optimism, +32 clock (live
          $2446a), +52 the site's feature record, +60 explosives carried (live $2446c)
  $2c3d6  = 96(A6), the current character
  $2a150  the feature list: kind byte (bit 7 enemy held, bits 0-6 n), a byte, x.w, y.w, then n building words; the
          building's first byte: bits 0-4 the type ($10 Ruin), bit 5 used (a Store or Magazine already emptied, a
          Garage's vehicle taken, the second station of a cable-car pair), bit 6 a charge planted, bit 7 guarded
  $2490a  17 words: explosive weight per type; $248e8 17 words: charges per type for this saboteur (`$44fc`)
  $248c6  17 words: minutes to plant per type
  $24468  charges planted on this screen; $24470 the site's building count
  $2c188  20 bytes: buildings blown up, by type (the report's DESTROYED column)
  $24e8c  -1 once the Headquarters is blown up (the period end's win test `$118ba`)
"""
A6 = 0x2c376
CUR = A6 + 96            # $2c3d6
PERF = A6 + 136          # $2c3fe, the saboteur's performance word ($4d6e/$4dee with category 0: Sabotage +14)
RECS, FEAT = 0x2b194, 0x2a150
WEIGHT, CHARGES, MINUTES = 0x2490a, 0x248e8, 0x248c6
PLANTED, CLOCK, EXPL, COUNT, MORALE = 0x24468, 0x2446a, 0x2446c, 0x24470, 0x2553c
DESTROYED, HQ_GONE = 0x2c188, 0x24e8c
CABLE, HQ, RUIN = 1, 0xf, 0x10
SUPPLYISH = (0xb, 0xc, 0xd, 0xe)   # Warehouse, Synthesis Plant, Factory, Radio Station: +5 Morale
BRANCH = {}


def hit(name):
    BRANCH[name] = BRANCH.get(name, 0) + 1


def rec(m):
    return RECS + 0x4a * m.w(CUR)


def site(m):
    return int.from_bytes(m.b[rec(m) + 52:rec(m) + 56], 'big') & 0xffffff


def charges(m):
    """`$4516..$453a` (tail of `$44fc`): charges[t] = weight[t] / (perf + 70) + 1, divu (word quotient). A divisor
    of 0 (perf $ffba) traps to the bare-`rte` zero-divide vector and leaves the weight as the quotient."""
    d = (m.w(PERF) + 70) & 0xffff
    for t in range(17):
        q = m.w(WEIGHT + 2 * t) // d if d else m.w(WEIGHT + 2 * t)
        m.setw(CHARGES + 2 * t, (q + 1) & 0xffff)


def toggle(m, i):
    """`$404e..`: a click on building cell i. Outside the site's buildings nothing happens. Otherwise bit 6 of the
    building flips; planting costs its minutes and charges, and is undone at once when the charges run out
    (the explosives word going negative); removing a charge refunds both."""
    if i >= m.w(COUNT):
        hit('toggle:outside')
        return
    b = site(m) + 6 + 2 * i
    was = m.u8(b) & 0x40
    m.set8(b, m.u8(b) ^ 0x40)
    t2 = 2 * (m.u8(b) & 0x1f)
    if not was:
        m.setw(PLANTED, m.w(PLANTED) + 1)
        m.setw(CLOCK, m.w(CLOCK) + m.w(MINUTES + t2))
        e = (m.w(EXPL) - m.w(CHARGES + t2)) & 0xffff
        m.setw(EXPL, e)
        if not e & 0x8000:
            hit('toggle:plant')
            return
        hit('toggle:short')
        m.set8(b, m.u8(b) & ~0x40)
    else:
        hit('toggle:remove')
    m.setw(PLANTED, m.w(PLANTED) - 1)
    m.setw(CLOCK, m.w(CLOCK) - m.w(MINUTES + t2))
    m.setw(EXPL, m.w(EXPL) + m.w(CHARGES + t2))


def morale_gain(m, kind, t):
    """`$4340` + `$5816`: 5 Morale, +5 at an enemy-held site, +5 for a Warehouse, Synthesis Plant, Factory or Radio
    Station; then capped at (Optimism + 500) / 3."""
    d = 5 + (5 if kind & 0x80 else 0) + (5 if t in SUPPLYISH else 0)
    v = (m.w(MORALE) + d) & 0xffff
    cap = (m.u8(rec(m) + 6) + 500) // 3
    hit('morale:capped' if v > cap else 'morale:raised')
    m.setw(MORALE, min(v, cap))


def blast_one(m):
    """`$41f6..$4272`: the first building of the site with a charge becomes a Ruin (bits 5 and 6 kept, guard bit 7
    dropped); its type is counted; the Headquarters sets the win flag; a Cable Car Station also ruins the other
    station of its pair (the record after it, or before it when bit 5 is set). Returns the building byte's address."""
    s = site(m)
    kind = m.u8(s)
    a = s
    while not m.u8(a + 6) & 0x40:
        a += 2
    t = m.u8(a + 6) & 0x1f
    morale_gain(m, kind, t)
    m.set8(DESTROYED + t, m.u8(DESTROYED + t) + 1)
    if t == HQ:
        hit('blast:hq')
        m.setw(HQ_GONE, 0xffff)
    elif t == CABLE:
        hit('blast:cable')
        other = a - 2 if m.u8(a + 6) & 0x20 else a + 14
        m.set8(other, (m.u8(other) & 0x20) | 0x10)
    else:
        hit('blast:held' if kind & 0x80 else 'blast:free')
    m.set8(a + 6, (m.u8(a + 6) & 0x60) | 0x10)
    return a + 6


def clear_one(m):
    """`$429e..$42c4`: after the explosion is drawn, bit 6 comes off the first building that has it."""
    a = site(m)
    while not m.u8(a + 6) & 0x40:
        a += 2
    m.set8(a + 6, m.u8(a + 6) & 0xbf)


def cancel(m):
    """`$482e`: leaving the screen by its icon takes every planted charge back, refunding charges and minutes."""
    s = site(m)
    for j in range(m.u8(s) & 0x7f):
        b = s + 6 + 2 * j
        if m.u8(b) & 0x40:
            m.set8(b, m.u8(b) & ~0x40)
            t2 = 2 * (m.u8(b) & 0x1f)
            m.setw(EXPL, m.w(EXPL) + m.w(CHARGES + t2))
            m.setw(CLOCK, m.w(CLOCK) - m.w(MINUTES + t2))
