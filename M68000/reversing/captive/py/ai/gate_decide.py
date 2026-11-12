"""Differential gate for the creature-group decision rule at the head of $10304 (federation, A6 = $1b5ce).

For each trial, from a base snapshot: poke one group record (position, facing/flag byte 5, lead type byte 8), the
party position 26/28(A6) and the frame RNG 15530(A6) (all LABELLED POKES that build the routine's inputs), call
$10304 with A0 = record, A5 = $93fe, D7 = record size, interrupts masked, and stop at the first decision label it
reaches. Compare with model() below, written from the code. Usage: gate_decide.py <snap> <trials> [seed]"""
import os, sys, random, struct; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from cap import *

LABELS = {0x10732: 'SPECIAL', 0x10464: 'WANDER', 0x1045e: 'FORGET', 0x103be: 'ATTACK', 0x10408: 'TURN_ATTACK',
          0x1050e: 'TURN', 0x104c6: 'FORWARD', 0x104f6: 'BEHIND_TURN'}
TB2C = 0x10b2c   # per-type byte: 1 = may attack from a distance (read from RAM below)

def model(cx, cy, face, f5, typ, px, py, rng, p2, ranged):
    if f5 & 0x20: return 'SPECIAL'
    if not f5 & 8 or typ in (6, 8): return 'WANDER'
    dx, dy = abs(cx - px), abs(cy - py)
    near = False
    def aim(d, dist, from_trail):
        if not from_trail and d == face:
            if dist > 1 and not ranged: return 'FORWARD'
            if dist > 1 and rng <= 0x31e0: return 'FORWARD'
            return 'ATTACK'
        rel = (face - d) & 3
        if rel == 0: return 'FORWARD'
        if rel == 2: return 'FORWARD' if near else 'BEHIND_TURN'
        if rng > 0x7d0 or not ranged: return 'TURN'
        return 'TURN_ATTACK'
    def trail():
        if f5 & 0x40: return 'WANDER'
        d = (p2 >> 3) & 7
        if d > 3: return 'FORGET'
        return aim(d, None, True)
    if dx == 0:
        if dy == 0: return 'WANDER'
        if dy > 6: return trail()
        return aim(2 if cy <= py else 0, dy, False)
    if dy != 0:
        near = dx <= 6 and dy <= 6
        return trail()
    if dx > 6: return trail()
    return aim(3 if cx <= px else 1, dx, False)

def main():
    snap, n = sys.argv[1], int(sys.argv[2]); random.seed(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    s = srv(snap)
    rec = A6 + 4532; size = struct.unpack('>h', s.read(rec + 2, 2))[0]
    tb = s.read(TB2C, 64); p2 = s.read(A6 + 11322, 2048)
    fork = s('fork')['id']
    ok = 0; tally = {}; bad = []
    for t in range(n):
        s('restore', id=fork)
        px, py = random.randrange(2, 62), random.randrange(1, 15)
        cx = min(63, max(0, px + random.randint(-8, 8))); cy = min(31, max(0, py + random.randint(-8, 8)))
        if random.random() < 0.4: cx = px if random.random() < 0.5 else cx; cy = py if cx != px else cy
        face = random.randrange(4)
        f5 = face | random.choice([0, 8, 8, 0x18, 0x18, 0x18]) | (0x40 if random.random() < 0.1 else 0) | (0x20 if random.random() < 0.03 else 0)
        typ = random.choice([1, 2, 0xc, 0xe, 0xd, 3, 6, 8])
        rng = random.randrange(0x10000) if random.random() < 0.7 else random.choice([0x31e0, 0x31e1, 0x7d0, 0x7d1, 0, 0x100])
        pv = p2[cy * 64 + cx] if random.random() < 0.6 else random.randrange(256)
        for a, w, v in [(A6 + 11322 + cy * 64 + cx, 1, pv), (rec, 1, cx), (rec + 1, 1, cy), (rec + 5, 1, f5), (rec + 8, 1, typ),
                        (A6 + 26, 2, px), (A6 + 28, 2, py), (A6 + 15530, 2, rng), (A6 + 13564, 2, 3)]:
            s('poke', addr=a, width=w, value=v)
        r = s.call(0x10304, max_steps=20000, stops=list(LABELS)[1:] + [0x10732], a0=rec, a5=0x93fe, d7=size)
        got = LABELS.get(int(r['pc'].lstrip('$'), 16), r['pc'])
        want = model(cx, cy, face, f5, typ, px, py, rng, pv, tb[typ])
        tally[want] = tally.get(want, 0) + 1
        if got == want: ok += 1
        elif len(bad) < 15: bad.append((cx, cy, face, hex(f5), typ, px, py, hex(rng), hex(pv), want, got))
    print(f'{ok}/{n} match'); print('by label', tally)
    for b in bad: print('MISMATCH', b)
    s.close()

if __name__ == '__main__':
    main()
