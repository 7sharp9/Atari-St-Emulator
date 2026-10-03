"""x9_verb_matrix.py: callcap of the verb handlers (table $00ffba) on a scratch script, on live objects, reading the exact record bytes each verb changes (the fields of the table in the report).
For each verb: the targeted field before -> after (hex), operand bytes consumed (A1 advance) and 2270(A5) (the condition byte) for the COND verbs.  Counts n of m checks that match the expected transition.
usage: x9_verb_matrix.py"""
import sys
from lab import *
BUF = 0x7f000
def table(r): return [0xffba + int.from_bytes(r.mem(0xffba + 2 * i, 2), 'big') for i in range(94)]
def put(r, script):
    s = (bytes(script) + bytes([0x17] * 8)); s += bytes(-len(s) % 4)
    for i in range(0, len(s), 4): r.cmd('w %x %s' % (BUF + i, s[i:i + 4].hex()))
def call(r, tab, verb, script, a0=None):
    put(r, script)
    regs = 'A1=%x A4=7f100' % BUF
    if a0: regs += ' A0=%x' % a0
    res = callcap(r, tab[verb], regs)
    res['da1'] = res['regN'][9] - BUF
    return res
def after(r, res, addr, n=1):
    cur = bytearray(r.mem(addr, n))
    for i in range(n):
        if addr + i in res['delta']: cur[i] = res['delta'][addr + i][1]
    return bytes(cur)
OK = BAD = 0
def chk(label, cond):
    global OK, BAD
    OK += bool(cond); BAD += (not cond); print('%-100s %s' % (label, 'ok' if cond else 'BAD'))
# ------------------------------------------------ CAVERN: header flag bits
r = start(SN('CAVERN', 'scratchpad/cadaver/gameplay_empire.snap')); passes(r, 2); tab = table(r)
oid = 412; rec = rec_of(r, oid); idb = [oid >> 8, oid & 0xff]
f3 = lambda res: after(r, res, rec + 3)[0]
b0 = r.mem(rec + 3, 1)[0]
chk('verb 17 (state bit 0 = 1): +3 %02x -> %02x, operands 2' % (b0, 0), True) if False else None
for verb, name, want in ((17, 'state bit 0 = 1', lambda x: x | 1), (18, 'state bit 0 = 0', lambda x: x & ~1), (20, 'state bit 1 = 1', lambda x: x | 2), (21, 'state bit 1 = 0', lambda x: x & ~2),
                         (24, 'state bit 0 ^= 1', lambda x: x ^ 1), (25, 'state bit 1 ^= 1', lambda x: x ^ 2), (26, 'HIDE (bit 7 = 1)', lambda x: x | 0x80)):
    for start_val in (b0, b0 | 3):
        wb(r, rec + 3, start_val)
        res = call(r, tab, verb, idb)
        chk('verb %2d %-18s +3 %02x -> %02x (expected %02x), operand bytes consumed %d' % (verb, name, start_val, f3(res), want(start_val) & 0xff, res['da1']), res['ret'] and f3(res) == want(start_val) & 0xff and res['da1'] == 2)
wb(r, rec + 3, b0)
for verb, name, bit in ((16, 'COND state bit 0', 1), (19, 'COND state bit 1', 2)):
    for v in (b0, b0 | 3):
        wb(r, rec + 3, v); res = call(r, tab, verb, idb)
        c = after(r, res, A5 + 2270)[0]
        chk('verb %2d %-18s +3=%02x -> 2270(A5) %d (expected %d)' % (verb, name, v, c, 1 if v & bit else 0), (c != 0) == bool(v & bit))
wb(r, rec + 3, b0)
# 30-33 act on the current object 348(A5)
wl(r, A5 + 348, rec)
for verb, name, want in ((31, 'cur state bit 0 = 0', lambda x: x & ~1), (32, 'cur state bit 0 = 1', lambda x: x | 1), (33, 'cur state bit 0 ^= 1', lambda x: x ^ 1)):
    for v in (b0, b0 | 1):
        wb(r, rec + 3, v); res = call(r, tab, verb, [])
        chk('verb %2d %-20s +3 %02x -> %02x (expected %02x), operands consumed %d' % (verb, name, v, f3(res), want(v), res['da1']), f3(res) == want(v) and res['da1'] == 0)
for v in (b0, b0 | 1):
    wb(r, rec + 3, v); res = call(r, tab, 30, []); c = after(r, res, A5 + 2270)[0]
    chk('verb 30 COND cur state bit 0: +3=%02x -> 2270(A5) %d' % (v, c), (c != 0) == bool(v & 1))
wb(r, rec + 3, b0)
# SHOW after HIDE in the same room
wb(r, rec + 3, b0 | 0x80); res = call(r, tab, 1, idb)
chk('verb  1 SHOW (hidden coin, same room): +3 %02x -> %02x, sprite array changes (callcap memory delta entries: %d)' % (b0 | 0x80, f3(res), len(res['delta'])), f3(res) == b0)
wb(r, rec + 3, b0)
# +15 bits through the verbs: LOCK/UNLOCK (54/55 bit 2), GOACTI/STOPACTI (67 clears bit 6, 68 sets bit 6)
f15 = lambda res: after(r, res, rec + 15)[0]; v15 = r.mem(rec + 15, 1)[0]
for verb, name, want in ((54, 'LOCK', lambda x: x | 4), (55, 'UNLOCK', lambda x: x & ~4), (68, 'STOPACTI', lambda x: x | 0x40), (67, 'GOACTI', lambda x: x & ~0x40)):
    for v in (v15, v15 | 0x44):
        wb(r, rec + 15, v); res = call(r, tab, verb, idb)
        chk('verb %2d %-9s +15 %02x -> %02x (expected %02x)' % (verb, name, v, f15(res), want(v)), f15(res) == want(v) and res['da1'] == 2)
wb(r, rec + 15, v15)
# anim: verbs 3/4 on the torch 413
a = rec_of(r, 413); ha = r.mem(a, 16); ab = a + ha[14]
def anim(res): return after(r, res, ab, 4), after(r, res, a + 15)[0]
wb(r, ab, 0xfe); wb(r, ab + 3, 4); wb(r, a + 15, 1)
res = call(r, tab, 3, [0x01, 0x9d]); an, f = anim(res)
chk('verb  3 GOANI on a halted ($fe) torch: anim %s +15 %02x   (expected 00 .. .. 05, bit 0 cleared)' % (an.hex(' '), f), an[0] == 0 and an[3] == 5 and f & 1 == 0)
wb(r, ab, 0xff); wb(r, a + 15, 1)
res = call(r, tab, 3, [0x01, 0x9d]); an, f = anim(res)
chk('verb  3 GOANI when the anim byte is $ff: anim %s +15 %02x   (expected unchanged: $ff stays, bit 0 stays)' % (an.hex(' '), f), an[0] == 0xff and f & 1 == 1)
wb(r, ab, 0x00); wb(r, a + 15, 0)
res = call(r, tab, 4, [0x01, 0x9d]); an, f = anim(res)
chk('verb  4 STOPANI on a running torch: anim byte %02x +15 %02x   (expected ff, bit 0 set)' % (an[0], f), an[0] == 0xff and f & 1 == 1)
r.close()
# ------------------------------------------------ L0 room 53: mover verbs on the patrolling urn 198
r = start(SN('URN53', 'scratchpad/cadaver/s87/b3/work/r16/s13_b.snap')); passes(r, 2); tab = table(r)
m = rec_of(r, 198); hm = r.mem(m, 16); mb = m + hm[13]
def mvb(res, n=14): return after(r, res, mb, n)
for st0, cur in ((0, 6), (1, 6), (4, 6), (3, 6)):
    wb(r, mb, st0); wb(r, mb + 1, cur)
    res = call(r, tab, 11, [0x00, 198]); x = mvb(res, 2)
    exp_cur = cur + 1 if st0 == 4 else cur
    chk('verb 11 GOMOVE with state %d cursor %d: state %d cursor %d (expected 0, %d)' % (st0, cur, x[0], x[1], exp_cur), x[0] == 0 and x[1] == exp_cur and res['da1'] == 2)
for st0 in (0, 3, 4):
    wb(r, mb, st0); res = call(r, tab, 12, [0x00, 198]); x = mvb(res, 1)
    chk('verb 12 STOPMOVE with state %d: state %d (expected 1)' % (st0, x[0]), x[0] == 1)
wb(r, mb, 1); res = call(r, tab, 69, [0x00, 198, 0x05, 0xfb, 0x02]); x = mvb(res, 6)
chk('verb 69 MOVE(198, 5, -5, 2): mover bytes 3..5 = %s (expected 05 fb 02), state byte untouched %d' % (x[3:6].hex(' '), x[0]), tuple(x[3:6]) == (5, 0xfb, 2) and res['da1'] == 5)
r.close()
# ------------------------------------------------ instance-block bits the creature verbs touch (class 3 object 237, L0 room 30)
r = start(SN('WATER30', 'scratchpad/cadaver/s85/explore/ck_g_water1.snap')); passes(r, 2); tab = table(r)
c = rec_of(r, 237); hc = r.mem(c, 16); ib = c + hc[12]
print('creature 237: inst block %s (class %02x)' % (r.mem(ib, hc[13] - hc[12]).hex(' '), sprites(r)[237]['tm'][22]))
def ibyte(res, k): return after(r, res, ib + k)[0]
for v in (0x00, 0x01):
    wb(r, ib + 6, v); res = call(r, tab, 89, [0x00, 237]); chk('verb 89 UNINV: inst+6 %02x -> %02x (expected %02x: bit 0 cleared)' % (v, ibyte(res, 6), v & ~1), ibyte(res, 6) == v & ~1 and res['da1'] == 2)
for v in (0x00, 0x04):
    wb(r, ib + 3, v); res = call(r, tab, 93, [0x00, 237]); chk('verb 93 DIRTY POTION: inst+3 %02x -> %02x (expected %02x: bit 2 set)' % (v, ibyte(res, 3), v | 4), ibyte(res, 3) == v | 4)
for v in (0x00, 0x80):
    wb(r, ib + 5, v); res = call(r, tab, 75, [0x00, 237]); chk('verb 75 SLEEP: inst+5 %02x -> %02x (expected %02x: bit 7 set)' % (v, ibyte(res, 5), v | 0x80), ibyte(res, 5) == v | 0x80)
    wb(r, ib + 5, v | 0x80); res = call(r, tab, 74, [0x00, 237]); chk('verb 74 WAKE: inst+5 %02x -> %02x (expected %02x: bit 7 cleared)' % (v | 0x80, ibyte(res, 5), v & 0x7f), ibyte(res, 5) == v & 0x7f)
r.close()
print('verb effect checks matching: %d of %d' % (OK, OK + BAD))
