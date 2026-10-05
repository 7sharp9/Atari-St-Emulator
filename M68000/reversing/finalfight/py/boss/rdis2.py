#!/usr/bin/env python3
"""rdis2.py: tools/rdis.py with table sizes capped by the next table base (fixed point over reruns).
rdis.py takes a dispatch table's entry count from its first word / 2; where two tables sit back to back and the first entry of the first points past
the second (DAMND $3d5b8 / $3d5c6) it runs on into the next table and decodes data as code. Here a table ends where another found table begins.
usage: rdis2.py [--rom f] [--end <hex addr where a table is known to end>]... <lo> <hi> <root> [<root>...]   (listing on stdout; tables and external calls at the end)"""
import os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '../../../..'))
sys.path.insert(0, os.path.join(root, 'tools'))
from disassemble import Disassembler
argv = sys.argv[1:]
rom_path = os.path.join(root, 'scratchpad/finalfight/ff_main.bin')
ENDS = set()
while argv and argv[0] in ('--rom', '--end'):
    if argv[0] == '--rom': rom_path = argv[1]
    else: ENDS.add(int(argv[1], 16))
    argv = argv[2:]
rom = open(rom_path, 'rb').read()
dis = Disassembler(rom, rom_base=0)
lo, hi = int(argv[0], 16), int(argv[1], 16)
roots = [int(a, 16) for a in argv[2:]]
BR = re.compile(r'^(bra|bsr|b[a-z]{2}|dbf|db[a-z]{2}|jsr|jmp)\b')
ABS = re.compile(r'\$([0-9a-f]+)(?:\.w|\.l)?$')
MOVEW = re.compile(r'move\.w \S+ == \$([0-9a-f]+)\+D(\d),D(\d)$')
IDXJ = re.compile(r'^(jmp|jsr) \S+ == \$([0-9a-f]+)\+D(\d)$')
JMPIDX = re.compile(r'^jmp 2\(PC,D(\d)\.w\)')

def run(known, labs):
    insns = {}; tables = {}; external = {}; work = list(roots); labels = set(roots)
    def entries(base):
        n = dis.rw(base) // 2
        nxt = [b for b in (set(known) | set(ENDS)) if b > base + 2]
        if nxt: n = min(n, (min(nxt) - base) // 2)
        return [(base + ((w ^ 0x8000) - 0x8000)) & 0xffffff for w in (dis.rw(base + 2 * i) for i in range(n))]
    def enq(a, src):
        if lo <= a < hi: labels.add(a); work.append(a)
        else: external.setdefault(a, set()).add(src)
    while work:
        a = work.pop(); prev = None
        while True:
            if a in insns or not (lo <= a < hi): break
            try: text, nxt = dis.decode_one(a)
            except Exception: insns[a] = ('(decode error)', a + 2); break
            insns[a] = (text, nxt)
            m = MOVEW.match(text)
            if m: prev = (int(m.group(1), 16), int(m.group(3)))
            if JMPIDX.match(text) and prev:
                b = prev[0]; ents = entries(b); tables[b] = ents
                for e in ents: enq(e, a)
                break
            mi = IDXJ.match(text)
            if mi:
                b = int(mi.group(2), 16); ents = entries(b); tables[b] = ents
                for e in ents: enq(e, a)
                if mi.group(1) == 'jmp': break
                a = nxt; prev = None; continue
            if not m: prev = None
            if BR.match(text):
                mm = ABS.search(text.split('==')[-1].strip()) if '==' in text else ABS.search(text)
                if mm: enq(int(mm.group(1), 16), a)
            op = text.split()[0]
            if op in ('rts', 'rte', 'bra', 'jmp', 'illegal') or op.startswith('trap'): break
            a = nxt
    return insns, tables, external, labels
known = set(); labs = set()
for _ in range(30):
    insns, tables, external, labels = run(known, labs)
    if set(tables) <= known: break
    known |= set(tables); labs |= labels
end_prev = None
for a in sorted(insns):
    text, nxt = insns[a]
    if end_prev is not None and a != end_prev: print('  ; ---- gap %x..%x (%d bytes) ----' % (end_prev, a, a - end_prev))
    if a in labels: print('L%x:' % a)
    print('  $%06x: %s' % (a, text)); end_prev = nxt
print('\n; tables')
for b in sorted(tables): print(';  $%x: %s' % (b, ' '.join('%d->%x' % (i, e) for i, e in enumerate(tables[b]))))
print('\n; external calls (target: callers)')
for t in sorted(external): print(';  $%x: %s' % (t, ' '.join('%x' % s for s in sorted(external[t]))))
