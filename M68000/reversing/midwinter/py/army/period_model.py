"""Model of the period end's own tests (ai.md section 5), transcribed from the routines `$ec8c` calls.

State (big-endian, absolute addresses):
  $2a150  the feature list (army_model.FEAT): kind byte (bit 7 enemy held, bits 0-6 n), a byte, x.w, y.w, n building
          words whose first byte & $1f is the building type ($10 Ruin once blown up)
  $24ba4  20 counts by building type over the sites the enemy does not hold; $24bb8 the same over held sites (`$f374`)
  $2b194  32 character records of $4a bytes: +32 clock, +52 the site's feature record, +63 the type of the building
          the character is in (negative: outside), +64 which building of the site
  $24be6  PRISONERS: characters in a Police Station of a held site (`$f3be`)
  $2c184, $2c182  the held Factory + Synthesis Plant + Warehouse + Radio Station count, and the held Heat Mine count,
          at the last rise; $24b7c the Morale every team member loses (`$ed88`)
  $2c172  the game clock in minutes; $24e8c set when the Headquarters is blown up; $24e8e the game is over, $24e90 the
          Free Villages have surrendered; $24be8 the report's message
  $2c186  the radio flag (`$f8d8`): 0 until the enemy holds no Radio Station, then 1 (the report sets it to -1)
  $2b16c  the team list (character numbers, a negative byte ends it)
"""
from army_model import FEAT, Mem  # noqa: F401

FREE, HELD, PRISONERS, LOSS = 0x24ba4, 0x24bb8, 0x24be6, 0x24b7c
RECS, TEAM, CLOCK = 0x2b194, 0x2b16c, 0x2c172
HEAT, SUPPLY, RADIO = 0x2c182, 0x2c184, 0x2c186
HQ_GONE, OVER, SURRENDER, MESSAGE = 0x24e8c, 0x24e8e, 0x24e90, 0x24be8
MSG_HQ, MSG_DAYS, MSG_HEAT = 0x24d64, 0x24dba, 0x24e18
HEAT_MINE, WAREHOUSE, SYNTH, FACTORY, RADIO_ST, POLICE = 10, 11, 12, 13, 14, 8
BRANCH = {}


def hit(name):
    BRANCH[name] = BRANCH.get(name, 0) + 1


def counts(m):
    """`$f374`: building counts by type, free and held."""
    for i in range(40):
        m.set8(FREE + i, 0)
    a = FEAT
    while m.u8(a):
        k = m.u8(a)
        table = HELD if k & 0x80 else FREE
        for j in range(k & 0x7f):
            t = m.u8(a + 6 + 2 * j) & 0x1f
            m.set8(table + t, m.u8(table + t) + 1)
        a += 6 + 2 * (k & 0x7f)


def prisoners(m):
    """`$f3be`: characters inside a Police Station of a site the enemy holds."""
    n = 0
    for c in range(32):
        r = RECS + 0x4a * c
        if m.s8(r + 63) < 0:
            continue
        p = int.from_bytes(m.b[r + 52:r + 56], 'big')
        if p == 0 or not m.u8(p) & 0x80:
            continue
        if m.u8(p + 6 + 2 * m.u8(r + 64)) & 0x1f == POLICE:
            n += 1
    hit('prisoners>0' if n else 'prisoners=0')
    m.setw(PRISONERS, n)


def morale_loss(m):
    """`$ed88`: 2 per rise in the held Factory + Synthesis Plant + Warehouse + Radio Station count and 10 per rise in
    held Heat Mines since the last rise; a fall only lowers the mark."""
    loss = 0
    s = sum(m.u8(HELD + t) for t in (FACTORY, SYNTH, WAREHOUSE, RADIO_ST))
    if s > m.w(SUPPLY):
        loss = (2 * (s - m.w(SUPPLY))) & 0xffff
    if s != m.w(SUPPLY):
        m.setw(SUPPLY, s)
    h = m.u8(HELD + HEAT_MINE)
    if h > m.w(HEAT):
        loss = (loss + 10 * (h - m.w(HEAT))) & 0xffff
    if h != m.w(HEAT):
        m.setw(HEAT, h)
    hit('loss>0' if loss else 'loss=0')
    m.setw(LOSS, loss)


def set_message(m, a):
    m.b[MESSAGE:MESSAGE + 4] = a.to_bytes(4, 'big')


def game_over(m):
    """`$118ba`: the Headquarters blown up, or 20 days ($7080 minutes) on the clock."""
    if m.w(HQ_GONE):
        hit('hq')
        set_message(m, MSG_HQ)
        m.setw(OVER, 0xffff)
    elif m.w(CLOCK) >= 0x7080:
        hit('20 days')
        set_message(m, MSG_DAYS)
        m.setw(OVER, 0xffff)


def heat_mines(m):
    """`$118f6`: no Heat Mine left outside the enemy's hands: the Free Villages surrender."""
    if m.u8(FREE + HEAT_MINE) == 0:
        hit('surrender')
        set_message(m, MSG_HEAT)
        m.setw(SURRENDER, 0xffff)


def radio(m):
    """`$f8d8`: once, when the enemy holds no Radio Station: all 32 characters join the team, their clocks set to the
    game clock (the list is written without an end byte)."""
    if m.sw(RADIO) < 0 or m.u8(HELD + RADIO_ST):
        return
    hit('radio')
    m.setw(RADIO, 1)
    for c in range(32):
        m.set8(TEAM + c, c)
        m.setw(RECS + 0x4a * c + 32, m.w(CLOCK))
