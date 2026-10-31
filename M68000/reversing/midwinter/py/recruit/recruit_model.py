"""Recruitment (ai.md section 8): who is present, the Decisions offer, and the answer from the 32x32 table.

Each function changes a Mem the way the routine changes RAM; gate_recruit.py checks them call by call.
"""
A6 = 0x2c376
CUR = A6 + 96          # the current character
FLAGS = A6 + 264       # bit 1: the recruit and k=10 offers are allowed
RECS = 0x2b194         # 32 character records of $4a bytes
TEAM = 0x2b16c         # the team list, character numbers ending with a negative byte
PRESENT = 0x22da6      # $12f2: the characters within 8 of the current one
OTHERS = 0x22dc8       # $4ade: those of them not in the team
CAND = 0x24474         # the character asked
ASKED = 0x24478        # copy of CAND once asked
SHOWN = 0x24476        # -1 once an answer is shown
BUSY = 0x24fa0
TEAM_SCORE = 0x2553c   # +40 per join, capped by $5816
ANSWER = 0x29d4b       # byte [candidate * 32 + asker]
NAMEFMT = 0x29d2b      # per character: bit 0 title, bit 1 first name, bit 2 surname in the answer line
DELTA = 0x24b84        # Morale added on a join, indexed by the whole answer byte (see recruit())
REPLIES, VERBS = 0x29c80, 0x29d00
TITLE, FIRST, SURNAME = 0x268d2, 0x267d2, 0x26752
TEXT = 0x2db3a         # the answer line
RADIO_USES = 0x2c174   # Kristiansen's radio calls left: 3 from the title screen on
RADIO_LIST = 0x70000   # $fab4: the characters not in the team
BRANCH = {}


def rec(c):
    return RECS + 0x4a * c


def coord(m, a):
    return (int.from_bytes(m.b[a:a + 4], 'big') >> 8) & 0xffff


def team(m):
    out, a = [], TEAM
    while m.u8(a) < 0x80:
        out.append(m.u8(a))
        a += 1
    return out


def present(m, cur, radius=8):
    """$12f2 with A1 = the current record: every other character within 8 in x and in y (positions >> 8) gets the
    current record's site pointer +52 and goes into PRESENT."""
    r0 = rec(cur)
    x0, y0 = coord(m, r0 + 34), coord(m, r0 + 38)
    out = PRESENT
    for c in range(32):
        r = rec(c)
        if r == r0:
            continue
        dx = (coord(m, r + 34) - x0) & 0xffff
        dy = (coord(m, r + 38) - y0) & 0xffff
        if (dx if dx < 0x8000 else (-dx) & 0xffff) < radius and (dy if dy < 0x8000 else (-dy) & 0xffff) < radius:
            m.b[r + 52:r + 56] = m.b[r0 + 52:r0 + 56]
            m.set8(out, c)
            out += 1
    m.set8(out, 0xff)


def others(m):
    """$4ade: PRESENT without the team members into OTHERS, at most 32 rows, padded with $ff to 33 bytes. Each row
    passes through CAND (the membership test $4b3a reads it)."""
    src, dst, n = PRESENT, OTHERS, 31
    while True:
        c = m.u8(src)
        src += 1
        if c >= 0x80:
            for _ in range(n + 1):
                m.set8(dst, 0xff)
                dst += 1
            return
        m.setw(CAND, c)
        if c not in team(m):
            m.set8(dst, c)
            dst += 1
        n -= 1
        if n < 0:
            m.set8(dst, 0xff)
            return


def offer(m, cur, any_building=False):
    """$1142, Decisions test k=6: the recruit icon ($489c) is offered when FLAGS bit 1 is set, the current character
    is inside a building (+63 >= 0) and someone in OTHERS is in the same building number +64."""
    r0 = rec(cur)
    if not m.w(FLAGS) & 2 or m.s8(r0 + 63) < 0:
        return False
    a = OTHERS
    while m.u8(a) < 0x80:
        if any_building or m.u8(rec(m.u8(a)) + 64) == m.u8(r0 + 64):
            return True
        a += 1
    return False


def cstr(m, a):
    a &= 0xffffff
    return bytes(m.b[a:m.b.index(0, a)])


def ptr(m, table, i):
    return int.from_bytes(m.b[table + 4 * i:table + 4 * i + 4], 'big')


def recruit(m, cand, cur, signed_delta=False, no_cap=False, transpose=False):
    """$496c, asking CAND from the recruit screen. The controls in gate_recruit.py flip the keyword switches."""
    m.setw(CAND, cand)
    if cand in team(m):
        BRANCH['member'] = BRANCH.get('member', 0) + 1
        m.setw(BUSY, 0xffff)
        return
    m.setw(ASKED, cand)
    b = m.u8(ANSWER + (cur * 32 + cand if transpose else cand * 32 + cur))
    if b < 0x80:
        BRANCH['join'] = BRANCH.get('join', 0) + 1
        a = TEAM
        while m.u8(a) < 0x80:
            a += 1
        m.set8(a, cand)                                   # $4b16: no new terminator is written
        r = rec(cand)
        m.b[r + 32:r + 34] = m.b[rec(cur) + 32:rec(cur) + 34]   # $ee08: the recruit takes the asker's clock
        # the table holds a Morale change per reply (+10, +10, 0, +40, 0, -20, +70, 0, +20, +20, +50, 0, -10, -20),
        # but the code indexes it by the whole byte and adds it unsigned
        d = m.s8(DELTA + (b >> 3)) if signed_delta else m.u8(DELTA + b)
        v = max(0, m.u8(r + 1) + d)
        m.set8(r + 1, v if v < 250 else 0xf9)
        t = m.w(TEAM_SCORE) + 40
        t = t if t < 250 else 0xf9
        cap = (m.u8(rec(m.w(CUR)) + 6) + 500) // 3      # $5816 reads $2c3d6, the same word as CUR: the asker's Optimism
        if not no_cap and cap < t:
            t = cap
        m.setw(TEAM_SCORE, t)
    else:
        BRANCH['refuse'] = BRANCH.get('refuse', 0) + 1
    line = b'"' + cstr(m, ptr(m, REPLIES, b >> 3)) + b'" ' + cstr(m, ptr(m, VERBS, b & 7)) + b' '
    f = m.u8(NAMEFMT + cand)
    for bit, table in ((1, TITLE), (2, FIRST), (4, SURNAME)):
        if f & bit:
            line += cstr(m, ptr(m, table, cand)) + b' '
    line = line[:-1] + b'.\0'
    m.b[TEXT:TEXT + len(line)] = line
    m.setw(SHOWN, 0xffff)
    m.setw(BUSY, 0xffff)


def radio_offer(m, cur, any_building=False):
    """$1102, Decisions test k=23 (the RADIO MESSAGE screen $f94c): FLAGS bit 1, calls left, fewer than 31 in the
    team, the current character is 12 (Olaf Kristiansen) and he is inside a building of type 14 (Radio Station)."""
    return bool(m.w(FLAGS) & 2 and m.w(RADIO_USES) and len(team(m)) < 31 and cur == 12
                and (any_building or m.u8(rec(cur) + 63) == 14))


def non_members(m):
    """$fab4: the characters 0..31 not in the team into RADIO_LIST, ending $ff; returns the count (D1)."""
    out = [c for c in range(32) if c not in team(m)]
    m.b[RADIO_LIST:RADIO_LIST + len(out) + 1] = bytes(out) + b'\xff'
    return len(out)


def radio_pick(m, rnd, mask=0x1f):
    """$fa78 after the random word $d598 (rnd, read from the run): non-member number (rnd & 31) mod count, appended
    to the team with a new terminator. With fewer than 32 non-members the low numbers come up more often."""
    n = non_members(m)
    c = m.u8(RADIO_LIST + (rnd & mask) % n)
    a = TEAM
    while m.u8(a) < 0x80:
        a += 1
    m.set8(a, c)
    m.set8(a + 1, 0xff)
    return c
