#!/usr/bin/env python3
"""Recursive-descent lister for the Final Fight program ROM (68000 space), kind 7/8 work.

usage: rdis.py <lo-hex> <hi-hex> <root-hex> [<root-hex> ...]

Follows bra/bcc/bsr/jsr/jmp to absolute targets inside [lo,hi), resolves the word-offset dispatch idiom
`move.w N(PC,Dn.w),D1 / jmp|jsr M(PC,D1.w)` (table base is printed by the disassembler as `== $base`; the first
word / 2 is the entry count), and prints reached instructions in address order with data gaps marked.
Calls out of range are listed at the end. Root, table and label sets go to stderr-free stdout sections.
"""
import os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '../../../..'))
sys.path.insert(0, os.path.join(root, 'tools'))
from disassemble import Disassembler

rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
dis = Disassembler(rom, rom_base=0)

lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
roots = [int(a, 16) for a in sys.argv[3:]]

BR = re.compile(r'^(bra|bsr|b[a-z]{2}|dbf|db[a-z]{2}|jsr|jmp)\b')
ABS = re.compile(r'\$([0-9a-f]+)(?:\.w|\.l)?$')
MOVEW = re.compile(r'move\.w \S+ == \$([0-9a-f]+)\+D(\d),D(\d)$')
IDXJ = re.compile(r'^(jmp|jsr) \S+ == \$([0-9a-f]+)\+D(\d)$')
JMPIDX = re.compile(r'^jmp 2\(PC,D(\d)\.w\)')

insns = {}
tables = {}
external = {}
work = list(roots)
labels = set(roots)


def table_entries(base):
    n = dis.rw(base) // 2
    return [(base + ((w ^ 0x8000) - 0x8000)) & 0xffffff for w in (dis.rw(base + 2 * i) for i in range(n))]


def addr_ok(a):
    return lo <= a < hi


def enqueue(a, src):
    if addr_ok(a):
        labels.add(a)
        work.append(a)
    else:
        external.setdefault(a, set()).add(src)


while work:
    a = work.pop()
    prev_move = None
    while True:
        if a in insns or not addr_ok(a):
            break
        try:
            text, nxt = dis.decode_one(a)
        except Exception:
            insns[a] = ('(decode error)', a + 2)
            break
        insns[a] = (text, nxt)
        m = MOVEW.match(text)
        if m:
            prev_move = (int(m.group(1), 16), int(m.group(3)))
        # computed dispatch via jmp 2(PC,Dx.w) (disassembler prints no `== base`)
        if JMPIDX.match(text) and prev_move:
            base = prev_move[0]
            ents = table_entries(base)
            tables[base] = ents
            for e in ents:
                enqueue(e, a)
            break
        mi = IDXJ.match(text)
        if mi:
            base = int(mi.group(2), 16)
            ents = table_entries(base)
            tables[base] = ents
            for e in ents:
                enqueue(e, a)
            if mi.group(1) == 'jmp':
                break
            a = nxt
            prev_move = None
            continue
        if not MOVEW.match(text):
            prev_move = None if not m else prev_move
        mb = BR.match(text)
        if mb:
            mm = ABS.search(text.split('==')[-1].strip()) if '==' in text else ABS.search(text)
            if mm:
                tgt = int(mm.group(1), 16)
                # abs.w targets are sign-extended; ff.. addresses never occur here
                enqueue(tgt, a)
        op = text.split()[0]
        if op in ('rts', 'rte', 'bra', 'jmp', 'illegal') or op.startswith('trap'):
            break
        a = nxt

# print
addrs = sorted(insns)
end_prev = None
for a in addrs:
    text, nxt = insns[a]
    if end_prev is not None and a != end_prev:
        print('  ; ---- gap %x..%x (%d bytes: data or unreached) ----' % (end_prev, a, a - end_prev))
    if a in labels:
        print('L%x:' % a)
    print('  $%06x: %s' % (a, text))
    end_prev = nxt
print('\n; tables')
for b in sorted(tables):
    print(';  $%x: %s' % (b, ' '.join('%d->%x' % (i, e) for i, e in enumerate(tables[b]))))
print('\n; external calls (target: callers)')
for t in sorted(external):
    print(';  $%x: %s' % (t, ' '.join('%x' % s for s in sorted(external[t]))))
