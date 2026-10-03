"""a3: gates_callcap.py -- measure all 29 event gates of the table $00fe84 by callcap on the dispatcher $011728 (D0 = event, A2 = $fe84,
A1 = scratch operand bytes at $7f000, A0 = a real type-6 template, queue-entry word poked into 1156(A5), byte 1167(A5) poked, 384(A5) and
348(A5) poked).  Accept = D0 0, reject = D0 -1 ($ffffffff).  Every case has a prediction written from reading the gate bodies
($00febe $00fece $00fee6 $00feea $00fefc $00ff10 $00ff26 $00ff38 $00ff4a $00ff4e $00ff88 $00ff98 $00ffa0); the script prints n of m
agreeing, plus the operand bytes consumed (A1 delta).  Usage (from M68000/): .venv/bin/python reversing/cadaver/py/secrets/overlay/events/gates_callcap.py [snap]
Expected: 'predictions matched m of m'."""
import sys, os
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../../..'))
OUTDIR = os.environ.get('OUTDIR') or os.path.join(ROOT, 'scratchpad/cadaver/s91_events'); os.makedirs(OUTDIR, exist_ok=True)   # scratch output (callcap json, caches, scan listings)
snap_arg = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, 'scratchpad/cadaver/gameplay_empire.snap')
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/verbs2')
import h as HH
from lib2 import afterl, afterb
from h import *
os.chdir(ROOT)
HH.TMP = OUTDIR   # callcap json goes here only
h = HH.H(snap_arg)
r = h.r
A5 = HH.A5

def set_entry(word, b1167=0, long384=0, long348=0):
    ww(r, A5 + 1156, word)
    wb(r, A5 + 1167, b1167)
    wl(r, A5 + 384, long384)
    wl(r, A5 + 348, long348)

OBJ_A = h.obj(2)       # target template (running object) used as A0
OBJ_X = h.obj(113)     # a second template resolved through the entry word
def inst0(oid):
    a = h.obj(oid); return h.r.mem(a + h.r.mem(a + 12, 1)[0], 8)

cases = []   # (event, label, script, word, b1167, expect 'A'/'R', expect consumed, extra dict)
def add(ev, label, script, word, exp, cons, **kw): cases.append((ev, label, bytes(script), word, kw.pop('b1167', 0), exp, cons, kw))

ACC = [0, 3, 5, 6, 7, 11, 14, 21, 22, 25, 27, 28]
for ev in ACC:
    for w in (0x0000, 0xffff, 0x1234):
        add(ev, 'no gate, word $%04x' % w, [], w, 'A', 0)
for ev in (2, 8):
    for w in (0x0000, 0xffff, 0x1234):
        add(ev, 'always rejects, word $%04x' % w, [], w, 'R', 0)
# event 1: operand byte vs byte 0 of the instance record of the object whose id is the entry word (positive id) or of the running object (word $ffff)
bX = inst0(113)[0]; bA = inst0(2)[0]
add(1, 'id 113: operand = inst byte0 $%02x' % bX, [bX], 113, 'A', 1, a0=OBJ_A)
add(1, 'id 113: operand = byte0 ^ 1', [bX ^ 1], 113, 'R', 1, a0=OBJ_A)
add(1, 'id 113: operand = running obj byte0 $%02x (differs)' % bA, [bA], 113, 'A' if bA == bX else 'R', 1, a0=OBJ_A)
add(1, 'word $ffff: operand = running obj byte0 $%02x' % bA, [bA], 0xffff, 'A', 1, a0=OBJ_A, l348=OBJ_A)
add(1, 'word $ffff: operand = byte0 ^ 1', [bA ^ 1], 0xffff, 'R', 1, a0=OBJ_A, l348=OBJ_A)
add(1, 'word $ffff, 348 -> id 113: operand = byte0 $%02x' % bX, [bX], 0xffff, 'A', 1, a0=OBJ_A, l348=OBJ_X)
# word compare events 4, 18, 26 (no wildcard)
for ev in (4, 18, 26):
    add(ev, 'equal $1234', [0x12, 0x34], 0x1234, 'A', 2)
    add(ev, 'low byte differs', [0x12, 0x35], 0x1234, 'R', 2)
    add(ev, 'high byte differs', [0x13, 0x34], 0x1234, 'R', 2)
    add(ev, '$ffff is NOT a wildcard', [0xff, 0xff], 0x1234, 'R', 2)
    add(ev, '$0000 is NOT a wildcard', [0x00, 0x00], 0x1234, 'R', 2)
    add(ev, '$0000 = $0000', [0x00, 0x00], 0x0000, 'A', 2)
    add(ev, '$ffff = $ffff', [0xff, 0xff], 0xffff, 'A', 2)
# event 9: wildcard = any operand with bit 15 set
add(9, 'equal $1234', [0x12, 0x34], 0x1234, 'A', 2)
add(9, 'differs', [0x12, 0x35], 0x1234, 'R', 2)
add(9, '$ffff wildcard', [0xff, 0xff], 0x1234, 'A', 2)
add(9, '$8000 wildcard (any bit 15)', [0x80, 0x00], 0x1234, 'A', 2)
add(9, '$8123 wildcard', [0x81, 0x23], 0x0042, 'A', 2)
add(9, '$7fff differs', [0x7f, 0xff], 0x1234, 'R', 2)
add(9, '$0000 is NOT a wildcard', [0x00, 0x00], 0x1234, 'R', 2)
add(9, '$0000 = $0000', [0x00, 0x00], 0x0000, 'A', 2)
# event 10: operand byte 1 vs 1167(A5), byte 2 vs 1157(A5) (low byte of the entry word)
add(10, 'both match', [0x55, 0x34], 0x1234, 'A', 2, b1167=0x55)
add(10, 'byte1 differs', [0x56, 0x34], 0x1234, 'R', 2, b1167=0x55)
add(10, 'byte2 differs', [0x55, 0x35], 0x1234, 'R', 2, b1167=0x55)
add(10, 'high byte of word irrelevant', [0x55, 0x34], 0xab34, 'A', 2, b1167=0x55)
add(10, '$ff not a wildcard', [0xff, 0xff], 0x1234, 'R', 2, b1167=0x55)
add(10, '$00 byte 1 vs 1167=0', [0x00, 0x34], 0x1234, 'A', 2, b1167=0x00)
# one byte vs 1157(A5)
for ev in (12, 13, 19, 20, 24):
    add(ev, 'byte = low byte of word', [0x34], 0x1234, 'A', 1)
    add(ev, 'byte differs', [0x35], 0x1234, 'R', 1)
    add(ev, 'high byte of word irrelevant', [0x34], 0xab34, 'A', 1)
    add(ev, '$ff not a wildcard', [0xff], 0x1234, 'R', 1)
    add(ev, '$00 not a wildcard', [0x00], 0x1234, 'R', 1)
    add(ev, '$00 = $00', [0x00], 0x1200, 'A', 1)
for ev in (15, 17):
    add(ev, 'byte = low byte of word; 348 := 384', [0x34], 0x1234, 'A', 1, l384=0x00071234, l348=0x00070001, exp348=0x00071234)
    add(ev, 'byte differs; 348 unchanged', [0x35], 0x1234, 'R', 1, l384=0x00071234, l348=0x00070001, exp348=0x00070001)
    add(ev, 'high byte irrelevant', [0x34], 0xab34, 'A', 1, l384=0x00071234, l348=0x00070001, exp348=0x00071234)
    add(ev, '$ff not a wildcard', [0xff], 0x1234, 'R', 1, l384=0x00071234, l348=0x00070001, exp348=0x00070001)
# 16: always accept; D4 bit 7 clear clears bit 5 of 3(A0)
add(16, 'keep (D4 bit7): 3(A0) untouched', [], 0x1234, 'A', 0, d4=0x80, a0=OBJ_A, tmpl3='same')
add(16, 'no keep: bit 5 of 3(A0) cleared', [], 0x1234, 'A', 0, d4=0x00, a0=OBJ_A, tmpl3='clr5')
# 23: always accept; XP 1192(A5) += byte 4 of the instance record, doubled by bit 2 of its byte 6
add(23, 'kill gate on running object', [], 0x1234, 'A', 0, a0=h.obj(483), xp=True)

def run_case(ev, label, script, word, b1167, exp, cons, kw):
    a0 = kw.get('a0', OBJ_A)
    set_entry(word, b1167, kw.get('l384', 0), kw.get('l348', a0))
    if 'l348' in kw: wl(r, A5 + 348, kw['l348'])
    pre3 = r.mem(a0 + 3, 1)[0]
    xp0 = r.l(A5 + 1192)
    d = h.call(0x11728, script, cap=20000, regs='D0=%x D6=%x D4=%x A2=fe84 A1=%x A0=%x' % (ev, ev, kw.get('d4', 0), HH.BUF, a0))
    d0 = d['regN'][0]
    got = 'A' if d0 == 0 else 'R' if d0 == 0xffffffff else '?%x' % d0
    ok = (got == exp) and d['ret'] and d['da1'] == cons
    note = ''
    if 'exp348' in kw:
        v = afterl(h, d, A5 + 348); ok = ok and v == kw['exp348']; note = ' 348(A5)=%08x' % v
    if kw.get('tmpl3'):
        v = afterb(h, d, a0 + 3); want = pre3 if kw['tmpl3'] == 'same' else pre3 & ~0x20
        ok = ok and v == want; note = ' 3(A0) %02x->%02x (pre bit5=%d)' % (pre3, v, (pre3 >> 5) & 1)
    if kw.get('xp'):
        inst = a0 + r.mem(a0 + 12, 1)[0]
        b4 = r.mem(inst + 4, 1)[0]; b6 = r.mem(inst + 6, 1)[0]
        want = xp0 + b4 * (2 if b6 & 4 else 1)
        v = afterl(h, d, A5 + 1192); ok = ok and v == want; note = ' XP %d->%d (byte4=%d byte6=%02x)' % (xp0, v, b4, b6)
    return ok, got, d, note

if __name__ == '__main__':
    good = 0
    for ev, label, script, word, b1167, exp, cons, kw in cases:
        ok, got, d, note = run_case(ev, label, script, word, b1167, exp, cons, kw)
        good += ok
        print('event %2d  %-52s -> %s (want %s) consumed %d (want %d) %s%s' % (ev, label, got, exp, d['da1'], cons, 'ok' if ok else 'BAD', note))
    print('predictions matched %d of %d' % (good, len(cases)))
    h.close()
