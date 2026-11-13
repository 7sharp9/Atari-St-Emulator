"""Resolve federation's computed PC-relative calls: `move.l #imm,Rn` then `jsr/lea d(PC,Rn.l)`.
Usage: pcrel_calls.py <federation.asm> [target_hex ...]  (prints call site -> target; filters by targets)."""
import re, sys
lines = open(sys.argv[1]).read().splitlines()
want = {int(t, 16) for t in sys.argv[2:]}
imm = {}
pat_mov = re.compile(r'\$([0-9a-f]+): movea?\.l #\$([0-9a-f]+),([DA]\d)')
pat_use = re.compile(r'\$([0-9a-f]+): (jsr|jmp|lea|pea) (-?\d+)\(PC,([DA]\d)\.l\)')
for ln in lines:
    m = pat_mov.search(ln)
    if m:
        imm[m.group(3)] = (int(m.group(1), 16), int(m.group(2), 16)); continue
    m = pat_use.search(ln)
    if m and m.group(4) in imm:
        at = int(m.group(1), 16); d = int(m.group(3)); v = imm[m.group(4)][1]
        if v & 0x80000000: v -= 1 << 32
        tgt = (at + 2 + d + v) & 0xffffff
        if not want or tgt in want:
            print(f'${at:06x} {m.group(2)} -> ${tgt:06x}')
