"""mover_model.py: Python transcription of the mover interpreter inside $00f71a (states 0, 2, program fetch $00f920, ops $00f95c-$00f9b4, per-axis stepping $00f8c0-$00f91c).
Mover block m (14-byte header + program) at rec+rec[13]:  m[0] state (0 run, 1 stopped, 2 wait, 3 externally driven, 4 program halted), m[1] program cursor, m[2] wait counter,
m[3..5] signed remaining step counts x,y,z, m[6..8] step size per frame per axis, m[9] frame delay (low nibble counts down, high nibble reloads it), m[10..12] state-3 request delta,
m[13] flags (bit 0 request pending, bit 1 / bit 2 push behaviour).  Program at m[14:]: 00 dx dy dz (set counters), 01 rel (jump rel bytes from the op), 02 (halt, state 4), 03 n (wait n frames), 04 n (event 12).
step(m) -> (delta (dx,dy,dz) or None, events, ended) where 'ended' = pass ended before the move code (waiting/halted/idle)."""

from collections import Counter
OPS = Counter()
def sb(v): return v - 256 if v >= 128 else v

def fetch(m, events):
    """$f920: read program ops until a move/wait/halt.  returns ('move', None) -> continue at $f7b6, or ('end', None)"""
    while True:
        D3 = m[1]; A3 = D3 + 0x0e
        op = m[A3]; A3 += 1; OPS[op] += 1
        if op == 0:
            m[3], m[4], m[5] = m[A3], m[A3 + 1], m[A3 + 2]
            m[1] = (D3 + 4) & 0xff
            return 'move'
        if op == 1:
            m[1] = (D3 + sb(m[A3])) & 0xff; continue
        if op == 2:
            m[0] = 4; return 'end'
        if op == 3:
            m[2] = m[A3]; m[0] = 2; m[1] = (D3 + 2) & 0xff; return 'end'
        if op == 4:
            events.append(('ev12', m[A3])); m[1] = (D3 + 2) & 0xff; return 'end'
        raise ValueError('op %d' % op)

def axis(m, i):
    """one axis of $f8c0/$f8e6/$f904: returns the signed step (0 if the counter is 0)"""
    c = m[3 + i]
    if c == 0: return 0
    if c < 128: m[3 + i] = c - 1; return m[6 + i]
    m[3 + i] = (c + 1) & 0xff; return -m[6 + i]

def move_part(m):
    D = [0, 0, 0]
    if m[3] != 0 or m[4] != 0 or m[5] != 0:
        for i in range(3): D[i] = axis(m, i)
        return tuple(D)
    return None

def step(m, state_override=None):
    events = []
    st = m[0]
    if st == 2:
        m[2] = (m[2] - 1) & 0xff
        if m[2] != 0: return None, events, True
        m[0] = 0
        if fetch(m, events) == 'end': return None, events, True
        st = 0; fromfetch = True
    elif st not in (0, 3):
        return None, events, True
    if st == 0:
        # $f7b6: delay nibble
        if m[9] != 0:
            L = (m[9] & 0xf) - 1
            if L >= 0: m[9] = (m[9] - 1) & 0xff; return None, events, True
            m[9] |= (m[9] >> 4)
        d = move_part(m)
        while d is None:                                   # counters empty: fetch (loops back to $f7b6 for op 0)
            if fetch(m, events) == 'end': return None, events, True
            if m[9] != 0:
                L = (m[9] & 0xf) - 1
                if L >= 0: m[9] = (m[9] - 1) & 0xff; return None, events, True
                m[9] |= (m[9] >> 4)
            d = move_part(m)
        return d, events, False
    # state 3 ($f7fa): delay nibble, then the pending request (m[10..12], flag m[13] bit 0) plus the counters, or the counters alone; never fetches a program op
    req = m[13] & 1
    if m[9] != 0:
        L = (m[9] & 0xf) - 1
        if L >= 0:
            m[9] = (m[9] - 1) & 0xff
            if not req: return None, events, True
        else:
            m[9] |= (m[9] >> 4)
    if req:
        D = [sb(m[10]), sb(m[11]), sb(m[12])]; m[13] &= ~1
        for i in range(3): D[i] += axis(m, i)
        return tuple(D), events, False
    d = move_part(m)
    return d, events, d is None
