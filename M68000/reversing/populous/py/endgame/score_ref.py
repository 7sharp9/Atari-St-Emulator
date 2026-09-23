"""score_ref.py - Python model of the score screen $1c858(lost).

score(m, lost) takes RAM at $1c858 entry and returns (rows, final_score, button):
rows = the 7 row strings at $225d8 + $2e*r + 6 after the routine has filled them,
final_score = $36cea after the bonuses, button = the button caption."""
from eg import *

def s32(v): v &= 0xffffffff; return v - (1 << 32) if v & 0x80000000 else v

def counts(m):
    """($1c93e..$1cc42) knights / towns / castles per (you, him)."""
    you = w(m, HUMAN)
    k = [0, 0]; t = [0, 0]; c = [0, 0]
    for i, e, d in entities(m):
        mine = 0 if d['side'] == you else 1
        if d['knight'] != 0 and d['str'] != 0:
            k[mine] += 1
        if d['flags'] == 1 and d['str'] != 0:
            if d['anim'] == 0x2a: c[mine] += 1
            else: t[mine] += 1
    return k, t, c

def score(m, lost):
    you, him = w(m, HUMAN), w(m, OTHER)
    rows = [bytearray(m[ROWS + 0x2e * r + 6: ROWS + 0x2e * r + 0x2e]) for r in range(7)]
    def put(r, off, s, cat=False):
        b = rows[r]
        if cat:
            off = b.index(0, off)
        b[off:off + len(s) + 1] = s.encode() + b'\0'
    put(0, 5, 'LOST' if lost == 1 else 'WON')
    bw = [sw(m, BATTLES + 2 * you), sw(m, BATTLES + 2 * him)]
    k, t, c = counts(m)
    for r, (a, b) in ((2, bw), (3, k), (4, t), (5, c)):
        put(r, 19, str(a).ljust(5))
        put(r, 19, str(b), cat=True)
    sc = s32(l(m, SCORE))
    if bw[0] > bw[1]:
        sc += 5000
    ou, oh = w(m, GOD + 0x2e * you + 14), w(m, GOD + 0x2e * him + 14)
    bit = 8
    while bit <= 0x100:
        if not (ou & bit): sc += 1000
        if oh & bit: sc += 1000
        bit <<= 1
    if w(m, 0x219b0):
        sc += (10 - sw(m, GOD + 0x2e * him + 16)) * 15   # muls of words: signed
    if lost == 0:
        sc = s32(sc * 10)
    if sc < 500: sc = 500
    if sc > 555555: sc = 515090
    put(6, 19, str(sc))
    rows = [bytes(b[:b.index(0)]).decode('latin1') for b in rows]
    btn = 'TRY IT AGAIN' if lost != 0 and w(m, 0x21d5e) != 0xffff else 'NEW GAME'
    return rows, sc, btn

if __name__ == '__main__':
    import sys
    m0, m1 = ram(sys.argv[1]), ram(sys.argv[2]); lost = int(sys.argv[3])
    rows, sc, btn = score(m0, lost)
    real = [rowtext(m1, r) for r in range(7)]
    ok = sum(a == b for a, b in zip(rows, real)) + (sc == s32(l(m1, SCORE)))
    for a, b in zip(rows, real): print('%-30s %-30s %s' % (a, b, a == b))
    print('score', sc, s32(l(m1, SCORE)), '%d/8' % ok)
