"""Differential gate for the regroup step at $10534 (federation, A6 = $1b5ce), the tail every group action reaches.

Per trial, from a base snapshot: LABELLED POKES build the inputs in group record 0 ($1c782 in this level, enough
room is borrowed from the records after it; the run is discarded by restore): the record's size word (1-9
members), flag byte +5 (facing bits 0-1, bit 2 = regroup pending, other bits random), every member's slot byte +1
(a random distinct slot 0-8 in the low nibble, random bits 4-7), and the frame RNG 15530(A6). It then calls $10534
with A0 = record, D7 = size, D6 = facing, interrupts masked, until the rts at the planted return, and compares the
record's +5 and every member's +1 byte with model() below, written from the code.
Usage: gate_regroup.py <snap> <trials> [seed]   (CONTROL=1 for the discriminating control)"""
import os, sys, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap import *

TAB = 0x10866          # per-facing 128-byte block: 7 preference rows, then 9 member-order rows (the code's $1089e)
CONTROL = os.environ.get('CONTROL') == '1'   # 1 = model with rng >= $afc8 and the last source slot: must lose matches
PAIR = 0x1063a         # two-member slot pair per facing

def model(f5, slots, rng, tab, pair):
    """slots: member +1 bytes. Returns (f5, slots) after $10534."""
    slots = list(slots)
    if not f5 & 4: return f5, slots
    f5 &= ~4 & 0xff
    n = len(slots); d7 = 8 + 8 * n; face = f5 & 3
    if d7 == 0x10:
        slots[0] = (slots[0] & 0xe0) | 0x14; return f5, slots
    if d7 == 0x50: return f5, slots
    if slots[0] & 0x10:
        if d7 == 0x18:
            for i in range(2): slots[i] = (slots[i] & 0xe0) | pair[face * 2 + i]
        return f5, slots
    if rng > (0xafc7 if CONTROL else 0xafc8): return f5, slots
    d3 = n - 1
    if d3 > 6: return f5, slots
    occ = 0
    for b in slots: occ |= 1 << (b & 0xf)
    pref = tab[(face * 16 + d3 - 1) * 8:][:d3 + 1]
    free = [p for p in pref if not occ >> (p & 0x1f) & 1]   # btst Dn,Dm uses the bit number mod 32
    if not free: return f5, slots
    d1 = free[0]
    order = tab[0x38 + (face * 16 + d1) * 8:][:8]
    src = [o for o in order if occ >> (o & 0x1f) & 1]
    if not src: return f5, slots
    d0 = src[-1] if CONTROL else src[0]
    for i, b in enumerate(slots):
        if (b & 0xf) == d0:
            slots[i] = (b & 0xf0) | d1; break
    return f5, slots

def main():
    snap, n = sys.argv[1], int(sys.argv[2]); random.seed(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    s = srv(snap)
    tab = s.read(TAB, 0x38 + 64 * 8 + 16); pair = s.read(PAIR, 8)
    rec = A6 + 4532
    fork = s('fork')['id']
    ok = 0; bad = []; tally = {}
    for t in range(n):
        s('restore', id=fork)
        m = random.choice([1, 2, 2, 3, 4, 4, 5, 6, 7, 8, 9])
        face = random.randrange(4)
        f5 = (random.randrange(256) & ~3 & 0xff) | face
        if random.random() < 0.85: f5 |= 4
        sl = random.sample(range(9), m)
        slots = [(random.randrange(16) << 4) | x for x in sl]
        if m == 1 and random.random() < 0.5: slots[0] = 0x14
        rng = random.randrange(0x10000) if random.random() < 0.8 else random.choice([0xafc8, 0xafc9, 0, 0xffff])
        s('poke', addr=rec + 2, width=2, value=8 + 8 * m)
        s('poke', addr=rec + 5, width=1, value=f5)
        for i, b in enumerate(slots):
            s('poke', addr=rec + 9 + 8 * i, width=1, value=b)
        s('poke', addr=A6 + 15530, width=2, value=rng)
        s.call(0x10534, A0=rec, D7=8 + 8 * m, D6=face)
        got5 = s.read(rec + 5, 1)[0]
        got = [s.read(rec + 9 + 8 * i, 1)[0] for i in range(m)]
        exp5, exp = model(f5, slots, rng, tab, pair)
        changed = 'moved' if exp != slots else 'same'
        tally[(m, changed)] = tally.get((m, changed), 0) + 1
        if (got5, got) == (exp5, exp): ok += 1
        elif len(bad) < 10: bad.append((m, hex(f5), [hex(x) for x in slots], hex(rng), hex(got5), [hex(x) for x in got], hex(exp5), [hex(x) for x in exp]))
    print(f'{ok}/{n} match')
    print('by members/outcome', dict(sorted(tally.items())))
    for b in bad: print('MISMATCH', b)
    s.close()

if __name__ == '__main__':
    main()
