"""Coarse census of code with no reference: candidate entries = the instruction after an rts/rte/jmp in the whole-image listing (data/full.asm, $2000-$43000),
kept if the next 3+ instructions decode cleanly; 'referenced' = the address appears as the target of a jsr/bsr/jmp/bra/Bcc/DBcc in the listing, or as a
big-endian longword or word in the resident image (pointer tables, jump tables).  Heuristic: prints candidates for manual reading, not a proof."""
import re, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
L = open(WORK + '/data/full.asm').read().split('\n')
ins = []
for l in L:
    m = re.match(r'\s+\$([0-9a-f]+): (.*)$', l)
    if m: ins.append((int(m.group(1), 16), m.group(2)))
addr2i = {a: i for i, (a, t) in enumerate(ins)}
r = ram()
img = bytes(r[0x2000:0x43000])
targets = set()
for a, t in ins:
    m = re.match(r'(jsr|bsr|jmp|bra|b[a-z]{2}|db[a-z]+)\s+(?:.*,)?#?(?:-?\d+ == )?\$([0-9a-f]+)(?:\.l)?\b', t)
    for mm in re.finditer(r'\$([0-9a-f]{3,6})', t):
        pass
    m2 = re.match(r'(jsr|bsr|jmp|bra|b[a-z]{2}|db[a-z]+)\b.*?\$([0-9a-f]+)', t)
    if m2: targets.add(int(m2.group(2), 16))
    m3 = re.search(r'== \$([0-9a-f]+)', t)
    if m3: targets.add(int(m3.group(1), 16))
    for mm in re.finditer(r'(?:lea|pea|move\.l #)\s*\$?([0-9a-f]{4,6})', t):
        targets.add(int(mm.group(1), 16))
    for mm in re.finditer(r'#\$([0-9a-f]{4,6}),', t): targets.add(int(mm.group(1), 16))
bad = re.compile(r'line-[AF]|\?\?\?|ori\.b #\$0,D0')
cands = []
for i, (a, t) in enumerate(ins):
    if i == 0: continue
    prev = ins[i-1][1]
    if not re.match(r'(rts|rte|jmp|bra )', prev): continue
    nxt = [x[1] for x in ins[i:i+4]]
    if any(bad.search(x) for x in nxt): continue
    if a in targets: continue
    if a >= 1 << 32: continue
    pat4 = a.to_bytes(4, 'big')
    if img.find(pat4) >= 0: continue
    # a relative table entry (word offsets) is not searched: report as candidate
    j = i; n = 0
    while j < len(ins) and not re.match(r'(rts|rte|jmp)', ins[j][1]) and n < 400: j += 1; n += 1
    cands.append((a, ins[min(j, len(ins)-1)][0] - a + 2, t))
print(len(cands), 'candidates')
for a, sz, t in cands:
    if 0xb000 <= a < 0x1f900: print(f'  ${a:05x} ~{sz:4d} bytes  first: {t}')
