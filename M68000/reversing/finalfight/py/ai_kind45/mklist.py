#!/usr/bin/env python3
"""Recursive-descent listing of a Final Fight 68000 range with dispatch tables resolved.

usage: mklist.py <lo> <hi> [root ...]      (hex; roots default to every aligned entry of the range's kind handlers)

Code reachable from the roots (bcc/bra/bsr/jsr/jmp targets and dispatch-table entries inside [lo,hi)) is
printed as instructions; a '>' in column 1 marks a branch target. Dispatch tables
(`move.w d(PC,Dn.w),D1 / jmp|jsr d2(PC,D1.w)`) are printed as `.tbl i -> target` lines. Everything not reached is
printed as `.word` rows, so data never decodes as garbage. The disassembler is tools/disassemble.py.
"""
import os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, '../../../..'))
sys.path.insert(0, os.path.join(root, 'tools'))
import disassemble as D

rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
dis = D.Disassembler(rom, rom_base=0)
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
roots = [int(a, 16) for a in sys.argv[3:]]

def rw(a): return int.from_bytes(rom[a:a + 2], 'big')

code = {}      # addr -> (text, next)
tables = {}    # table addr -> (count, base, [targets])
targets = set()
work = list(roots)
seen = set()
rx_tbl = re.compile(r'== \$([0-9a-f]+)\+D\d')
rx_tbl2 = re.compile(r'computed-dispatch table at \$([0-9a-f]+)')
rx_br = re.compile(r'^(?:b[a-z]{2}|bsr|bra|jsr|jmp|db[a-z]+)\s.*?\$([0-9a-f]+)(?:\.[wl])?$')

def add_table(T, count=None):
    if T in tables: return tables[T][2]
    if count is None:
        # entries are word offsets from T; the table ends where the first forward-pointing target begins
        minT = 1 << 30; i = 0
        while T + 2 * i < minT and i < 128:
            e = T + (rw(T + 2 * i) - 65536 if rw(T + 2 * i) & 0x8000 else rw(T + 2 * i))
            if e > T + 2 * i and e % 2 == 0: minT = min(minT, e)
            i += 1
        n = i
    else:
        n = count
    tg = [T + (rw(T + 2 * i) - 65536 if rw(T + 2 * i) & 0x8000 else rw(T + 2 * i)) for i in range(n)]
    tables[T] = (n, T, tg)
    return tg

while work:
    a = work.pop()
    while lo <= a < hi and a not in seen:
        seen.add(a)
        try:
            text, nxt = dis.decode_one(a)
        except Exception as e:
            code[a] = ('<error %s>' % e, a + 2); break
        code[a] = (text, nxt)
        # dispatch idioms
        m2 = rx_tbl2.search(text)
        if m2:
            tg = add_table(int(m2.group(1), 16))
            for t in tg:
                if t % 2: continue
                targets.add(t); work.append(t)
            code[a] = (text, a + 4)
            break
        m = rx_tbl.search(text)
        if m and text.startswith(('jsr', 'jmp')):
            T = int(m.group(1), 16)
            tg = add_table(T)
            for t in tg:
                if t % 2: continue
                targets.add(t); work.append(t)
            if text.startswith('jmp'): break
            a = nxt; continue
        mb = rx_br.match(text)
        if mb and not text.startswith('jmp (') :
            t = int(mb.group(1), 16)
            op = text.split()[0]
            if lo <= t < hi:
                targets.add(t); work.append(t)
            if op in ('bra', 'jmp'): break
        if text.startswith(('rts', 'rte')): break
        if text.startswith('jmp') and '(A' in text: break
        a = nxt

out = []
a = lo
tabaddr = {}
for T, (n, base, tg) in tables.items():
    for i in range(n): tabaddr[T + 2 * i] = (i, tg[i], T)
while a < hi:
    if a in code:
        text, nxt = code[a]
        out.append('%s $%06x: %s' % ('>' if a in targets else ' ', a, text))
        a = nxt
    elif a in tabaddr:
        i, t, T = tabaddr[a]
        out.append('  $%06x: .tbl[$%x][%d] -> $%x' % (a, T, i, t))
        a += 2
    else:
        # raw data run until next code or table address
        b = a; row = []
        while b < hi and b not in code and b not in tabaddr and len(row) < 8:
            row.append('%04x' % rw(b)); b += 2
        out.append('  $%06x: .word %s' % (a, ' '.join(row)))
        a = b
print('\n'.join(out))
