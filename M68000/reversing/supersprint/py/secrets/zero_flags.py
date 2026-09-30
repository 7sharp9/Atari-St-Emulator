"""zero_flags.py - A4-relative globals that are READ but only ever written with the constant 0 (clr / move #0) or never written:
candidates for permanently-disabled test/debug switches.  Arrays accessed through lea base+index are excluded (address taken)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach
from globals import info, split_ops, op_re
ins = reach.load()
zero_w = {}; nz_w = {}
for a, t in ins:
    if '(A4)' not in t: continue
    parts = t.split(None, 1); mn = parts[0]; rest = parts[1] if len(parts) > 1 else ''
    ops = split_ops(rest.split(' ==')[0])
    base = mn.split('.')[0]
    for idx, op in enumerate(ops):
        m = op_re.fullmatch(op.strip())
        if not m or base in ('lea', 'pea'): continue
        off = int(m.group(1))
        if base == 'clr' and len(ops) == 1: zero_w.setdefault(off, []).append(a)
        elif len(ops) == 2 and idx == 1 and base in ('move', 'movea'):
            if ops[0].strip() in ('#$0', '#0'): zero_w.setdefault(off, []).append(a)
            else: nz_w.setdefault(off, []).append(a)
        elif len(ops) == 2 and idx == 1 and base in ('add', 'sub', 'addq', 'subq', 'or', 'and', 'eor', 'neg', 'not', 'ori', 'andi', 'addi', 'subi', 'bset', 'bclr', 'asl', 'lsl', 'lsr', 'asr'):
            nz_w.setdefault(off, []).append(a)
        elif len(ops) == 1 and base in ('addq', 'subq', 'neg', 'not', 'st', 'seq', 'sne', 'scc', 'scs', 'bset'):
            nz_w.setdefault(off, []).append(a)
for off, d in sorted(info.items()):
    if d['a']: continue
    if not d['r']: continue
    if off in nz_w: continue
    w = zero_w.get(off, [])
    print('%6d(A4) reads %s  zero-writes %s' % (off, [hex(x) for x in d['r'][:5]], [hex(x) for x in w[:3]]))
