"""Recursive-descent listing of the Final Fight 68000 program ROM, so data tables do not decode as code.

    rdis.py <lo> <hi> <seed> [<seed> ...]     (hex)    seeds are code entry points inside [lo, hi)

Follows bsr/bra/bcc/dbf/jsr/jmp targets inside [lo, hi) and resolves the two PC-relative dispatch idioms
(`move.w N(PC,Dn.w),Dx` / `jmp|jsr M(PC,Dx.w)`, word table whose first word is 2*entries, and the long-table
`movea.l N(PC,Dn.w),A1`). Addresses in [lo, hi) never reached are printed as `.dw` runs. Output: stdout.
"""
import os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, '../../../..'))
sys.path.insert(0, os.path.join(root, 'tools'))
from disassemble import Disassembler  # noqa

rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
dis = Disassembler(rom, rom_base=0)
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
seeds = []
override = {}
for a in sys.argv[3:]:
    if ':' in a:
        t, n = a.split(':'); override[int(t, 16)] = int(n)
    else:
        seeds.append(int(a, 16))
rw = dis.rw

tgt_re = re.compile(r'(?:^|\s)(?:bsr|bra|b[a-z]{2}|jsr|jmp)\s+\$([0-9a-f]+)')
dbf_re = re.compile(r'dbf D\d,#-?\d+ == \$([0-9a-f]+)')
pcx_re = re.compile(r'==\s*\$([0-9a-f]+)\+D')
code = {}   # addr -> text
datanote = {}
work = list(seeds)
seen = set()
while work:
    a = work.pop()
    while lo <= a < hi and a not in seen:
        seen.add(a)
        try:
            text, nxt = dis.decode_one(a)
        except Exception:
            break
        code[a] = (text, nxt)
        for m in (tgt_re.search(text), dbf_re.search(text)):
            if m:
                t = int(m.group(1), 16)
                if lo <= t < hi:
                    work.append(t)
        mm = pcx_re.search(text)
        if mm and ('jmp' in text or 'jsr' in text or text.startswith('move.w') or text.startswith('movea')):
            T = int(mm.group(1), 16)
            if text.startswith('move.w') or ('jsr' in text) or ('jmp' in text):
                if text.startswith('move.w'):
                    n = 64; bound = 1 << 30; i = 0
                    while i < n and 2 * i < bound:
                        bound = min(bound, rw(T + 2 * i)); i += 1
                    n = override.get(T, i)
                    datanote[T] = ('wtab', n)
                    for i in range(n):
                        t = T + rw(T + 2 * i)
                        if lo <= t < hi:
                            work.append(t)
            elif text.startswith('movea.l'):
                datanote[T] = ('ltab', None)
                for i in range(8):
                    v = dis.rl(T + 4 * i)
                    if lo <= v < hi and v % 2 == 0:
                        work.append(v)
                    else:
                        break
        # stop conditions
        if text.startswith(('rts', 'rte', 'bra', 'jmp', 'illegal')) or '???' in text:
            break
        a = nxt

out = []
a = lo
while a < hi:
    if a in code:
        text, nxt = code[a]
        lab = ''
        if a in datanote: lab = ''
        out.append('  $%06x: %s' % (a, text))
        a = nxt
    else:
        # data run until next code addr
        b = a
        words = []
        while b < hi and b not in code and len(words) < 16:
            words.append('%04x' % rw(b)); b += 2
        out.append('  $%06x: .dw %s%s' % (a, ' '.join(words), '   ; ' + str(datanote[a]) if a in datanote else ''))
        a = b
print('\n'.join(out))
