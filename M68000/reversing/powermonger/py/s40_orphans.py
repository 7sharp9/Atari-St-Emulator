"""s40_orphans.py - routine starts of powermonger_orig.sym that nothing in the image refers to.

    cd M68000 && python reversing/powermonger/py/s40_orphans.py [ram.ram] [listing.asm]

A symbol start counts as referenced if any of these names it: a 4-byte literal in the text (any even
offset), an operand in the whole-image listing (`$addr` or `== $addr`), a signed or unsigned word
at p with p + w == addr (or p + 2 + w), or a word in the 0x120 bytes after any symbol read as
symbol + w (the jump-table idiom, whose base is often not a symbol). Defaults: scratchpad/pm123/win/m1_s0.ram
and the whole-image listing scratchpad/pm130/audit/all_0_100000.asm (`disassemble.py --snap <snap> --all 0 100000`;
check it reaches $ffffc, a truncated listing reads as "no caller"). The runtime text lies at
$10a6 .. $10a6 + the text length of SPRITE40.DAT's inner program ($1b3e4 + 4). Prints the 14 survivors of the 133rd pass;
strategy.md "Original names" says what each one is.
"""
import collections
import os
import re
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
ram_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'scratchpad', 'pm123', 'win', 'm1_s0.ram')
lst_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'scratchpad', 'pm130', 'audit', 'all_0_100000.asm')
sym_path = os.path.join(ROOT, 'reversing', 'powermonger', 'powermonger_orig.sym')

r = open(ram_path, 'rb').read()
LO, HI = 0x10a6, 0x10a6 + 0x1b3e4 + 4
rows = [l.rstrip().split('\t') for l in open(sym_path, encoding='utf-8') if not l.startswith('#')]
names = collections.defaultdict(list)
for a, n, k in rows:
    if k == '# T':
        names[int(a, 16)].append(n)
S = set(names)

lit = collections.Counter()
for i in range(LO, HI - 3, 2):
    v = struct.unpack('>I', r[i:i + 4])[0]
    if v in S:
        lit[v] += 1

lst = collections.Counter()
for m in re.finditer(r'(?:\$|== \$)0*([0-9a-f]{4,6})\b', open(lst_path).read()):
    v = int(m.group(1), 16)
    if v in S:
        lst[v] += 1                       # the symbol's own "$addr:" line counts once

rel = collections.Counter()
for p in range(LO, HI - 1, 2):
    w = struct.unpack('>h', r[p:p + 2])[0]
    for t in (p + w, p + 2 + w):
        if t in S:
            rel[t] += 1

tab = collections.Counter()
for b in sorted(S):
    for p in range(b, min(b + 0x120, HI - 1), 2):
        for fmt in ('>h', '>H'):
            t = b + struct.unpack(fmt, r[p:p + 2])[0]
            if t in S and t != b:
                tab[t] += 1

direct = [a for a in sorted(S) if lit[a] == 0 and lst[a] <= 1 and rel[a] == 0]
dead = [a for a in direct if tab[a] == 0]
print(f'{len(S)} routine starts; {len(direct)} without a direct reference; {len(dead)} after the table scan')
for a in dead:
    print('%06x' % a, ','.join(names[a]))
