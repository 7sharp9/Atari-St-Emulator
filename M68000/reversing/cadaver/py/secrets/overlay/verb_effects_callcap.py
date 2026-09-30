"""verb_effects_callcap.py [snap]: the effect of the arithmetic and variable verbs of the object-script table, measured on
the real handlers with `callcap` (A1 = a scratch script, memory delta read back).  Pins the names in verb_decode.VERBS
that a wrong reading of `(A5)+1188` (gold, longword) and `(A5)+1192` (XP, longword) would swap: 5, 6, 13, 85, 86 (gold and
XP), 38, 39 (script byte variables at 2282(A5)), 62, 63 (any A5 word or byte), 45 (health `1174(A5)`), 79 and 81 (`2520(A5)`).

Run from M68000/: `uv run python reversing/cadaver/py/secrets/overlay/verb_effects_callcap.py`.  Expected: every line ok."""
import sys, re
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
from ov import *

snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/cadaver/gameplay_empire.snap'
BUF = 0x7f000
r = Repl(snap)
tab = [0xffba + int.from_bytes(r.mem(0xffba + 2 * i, 2), 'big') for i in range(94)]
ok = bad = 0


def run(v, script, pre=()):
    """poke `pre` = [(off, hexbytes)] at (A5)+off, call verb v with A1 -> script; returns {a5 offset: bytes after} for
    every changed byte, from the callcap delta."""
    s = (bytes(script) + bytes([0x17] * 24))[:24]
    for i in range(0, 24, 4): r.cmd('w %x %s' % (BUF + i, s[i:i + 4].hex()))
    for off, hx in pre:
        for i, x in enumerate(bytes.fromhex(hx)): wb(r, A5 + off + i, x)
    out = r.cmd('callcap %x 300000 - A1=%x A4=7f100' % (tab[v], BUF))
    ch = {}
    for l in out:
        m = re.match(r'mem \$([0-9a-f]+) \$([0-9a-f]+)->\$([0-9a-f]+)', l)
        if m: ch[int(m.group(1), 16) - A5] = int(m.group(3), 16)
    return ch, any('returned' in l for l in out)


def long_at(off): return r.l(A5 + off)


def check(label, cond):
    global ok, bad
    if cond: ok += 1
    else: bad += 1
    print('%-58s %s' % (label, 'ok' if cond else 'BAD'))


def pokel(off, val): r.cmd('w %x %08x' % (A5 + off, val))


def after(v, script, pre, off, n):
    """value of n bytes at (A5)+off after the verb ran (delta over the pre-state; unchanged bytes read back from the pre-state)"""
    ch, ret = run(v, script, pre)
    cur = bytearray(r.mem(A5 + off, n))
    for i in range(n):
        if off + i in ch: cur[i] = ch[off + i]
    return int.from_bytes(cur, 'big'), ret


G, X = 1188, 1192
pokel(G, 1000); pokel(X, 100)
g0, x0 = long_at(G), long_at(X)
# verbs 5 and 85 read their operand but never add it: `move.w #$1a,D0` (the sound id, `$0102e0`) or `move.w #$24,D0` (`$0102d4`)
# overwrites the low word of D0 before `add.l D0,1192(A5)` at `$0102ea`, and `$0158f8` (the sound routine) restores D0.
for opnd in (0, 1, 10, 200):
    x, _ = after(5, [opnd], (), X, 4); g, _ = after(5, [opnd], (), G, 4)
    check('verb 5  [%02x]     XP %d -> %d (+26 = sound id $1a, operand ignored), gold same' % (opnd, x0, x), x == x0 + 26 and g == g0)
for opnd in ((0, 5), (0x7f, 0xff)):
    x, _ = after(85, opnd, (), X, 4)
    check('verb 85 [%02x%02x]   XP %d -> %d (+26, positive word)' % (opnd[0], opnd[1], x0, x), x == x0 + 26)
for opnd in ((0xff, 0xfb), (0x80, 0x00)):
    x, _ = after(85, opnd, (), X, 4)
    check('verb 85 [%02x%02x]   XP %d -> %d (negative word: adds $ffff0024, then clamped to 0)' % (opnd[0], opnd[1], x0, x), x == 0)
g, _ = after(6, [20], (), G, 4); x, _ = after(6, [20], (), X, 4)
check('verb 6  [14]     gold %d -> %d (+20), XP %d -> %d (+5)' % (g0, g, x0, x), g == g0 + 20 and x == x0 + 5)
g, _ = after(13, [3], (), G, 4); x, _ = after(13, [3], (), X, 4)
check('verb 13 [03]     gold %d -> %d (-3), XP %d -> %d (same)' % (g0, g, x0, x), g == g0 - 3 and x == x0)
g, _ = after(86, [0, 40], (), G, 4); x, _ = after(86, [0, 40], (), X, 4)
check('verb 86 [0028]   gold %d -> %d (+40), XP %d -> %d (+10)' % (g0, g, x0, x), g == g0 + 40 and x == x0 + 10)

V = 2282
b, _ = after(38, [3, 0x77], (), V + 3, 1); check('verb 38 [03 77]   VAR 3 -> $%02x' % b, b == 0x77)
b, _ = after(39, [3, 2], ((V + 3, '10'),), V + 3, 1); check('verb 39 [03 02]   VAR 3: $10 -> $%02x' % b, b == 0x12)
off = V + 10
w, _ = after(62, [(off >> 8) & 0x7f, off & 0xff, 0x12, 0x34], (), off, 2); check('verb 62 word form  (A5)+%d -> $%04x' % (off, w), w == 0x1234)
b, _ = after(62, [0x80 | (off >> 8), off & 0xff, 0x56], (), off, 1); check('verb 62 byte form  (A5)+%d -> $%02x' % (off, b), b == 0x56)
w, _ = after(63, [(off >> 8) & 0x7f, off & 0xff, 0, 5], ((off, '0064'),), off, 2); check('verb 63 word form  $0064 + 5 -> $%04x' % w, w == 0x69)
b, _ = after(63, [0x80 | (off >> 8), off & 0xff, 5], ((off, '64'),), off, 1); check('verb 63 byte form  $64 + 5 -> $%02x' % b, b == 0x69)

mx = r.w(A5 + 2516)
r.cmd('w %x %04x0000' % (A5 + 1174, 5))
hp, _ = after(45, [0, 3], (), 1174, 2); check('verb 45 [0003]   health 5 -> %d (max %d)' % (hp, mx), hp == 8)
r.cmd('w %x %04x0000' % (A5 + 1174, 5))
hp, _ = after(45, [0xff, 0xfe], (), 1174, 2); check('verb 45 [fffe]   health 5 -> %d' % hp, hp == 3)
rv, _ = after(79, [5, 9], (), 2520, 1); check('verb 79 [05 09]   RANDOM 5..9 -> %d' % rv, 5 <= rv <= 9)
rv, _ = after(81, [3], ((V + 3, '2a'),), 2520, 1); check('verb 81 [03]      2520(A5) = VAR 3 ($2a) -> $%02x' % rv, rv == 0x2a)
# comparison verbs: the condition counter 2270(A5) is set to 7 first; a true condition makes it 8, a false one clears it to 0
C = 2270
def cond(v, script, pre=()):
    c, _ = after(v, script, ((C, '07'),) + tuple(pre), C, 1)
    return {8: True, 0: False}.get(c, c)
for op, val, want, sym in ((0, 3, True, '>'), (0, 5, False, '>'), (0, 9, False, '>'), (1, 9, True, '<'), (1, 5, False, '<'), (1, 3, False, '<'),
                           (2, 5, True, '=='), (2, 4, False, '=='), (3, 4, True, '!='), (3, 5, False, '!='), (7, 4, True, '!='), (7, 5, False, '!=')):
    got = cond(40, [3, op, val], ((V + 3, '05'),))
    check('verb 40 [03 %02x %02x]   VAR 3 = 5: (5 %s %d) -> %s' % (op, val, sym, val, got), got == want)
    off = V + 10
    got = cond(64, [(off >> 8) & 0x7f, off & 0xff, 0, val, op], ((off, '0005'),))
    check('verb 64 word [%02x %02x] op %d  (5 %s %d) -> %s' % (off >> 8, off & 0xff, op, sym, val, got), got == want)
print('ok %d  bad %d' % (ok, bad))
r.close()
