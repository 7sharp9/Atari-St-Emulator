"""globals.py - classify every A4-relative global as written / read / address-taken from ss.asm (heuristic on the
operand position), and list the suspicious ones: written never read, read never written (besides the initialiser
block $11b24-$11b?? ), address-taken.  Offsets only; sizes are not tracked.  Usage: globals.py [--all]"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach

ins = reach.load()
DEST_ONLY = ('move.w', 'move.l', 'move.b', 'movea.l', 'movea.w', 'clr.w', 'clr.l', 'clr.b', 'st', 'sf', 'seq', 'sne')
RMW = ('add', 'sub', 'and', 'or', 'eor', 'neg', 'not', 'addq', 'subq', 'bset', 'bclr', 'bchg', 'asl', 'asr', 'lsl', 'lsr', 'addi', 'subi', 'ori', 'andi', 'eori', 'roxl', 'roxr', 'rol', 'ror')
READ_ONLY = ('cmp', 'cmpi', 'tst', 'btst', 'cmpa', 'cmpm')
op_re = re.compile(r'(-?\d+)\(A4\)')

def split_ops(s):
    ops, depth, cur = [], 0, ''
    for c in s:
        if c == '(': depth += 1
        if c == ')': depth -= 1
        if c == ',' and depth == 0:
            ops.append(cur); cur = ''
        else:
            cur += c
    if cur: ops.append(cur)
    return ops

info = {}  # off -> dict(w=[], r=[], a=[])
INIT = (0x11b24, 0x11f40)
for a, t in ins:
    if '(A4)' not in t: continue
    parts = t.split(None, 1)
    mn = parts[0]; rest = parts[1] if len(parts) > 1 else ''
    base = mn.split('.')[0]
    ops = split_ops(rest.split(' ==')[0])
    for idx, op in enumerate(ops):
        m = op_re.fullmatch(op.strip())
        if not m: continue
        off = int(m.group(1))
        d = info.setdefault(off, dict(w=[], r=[], a=[]))
        if base in ('lea', 'pea'):
            d['a'].append(a); continue
        if len(ops) == 2 and idx == 1:
            if mn in DEST_ONLY: d['w'].append(a)
            elif base in RMW: d['w'].append(a); d['r'].append(a)
            elif base in READ_ONLY: d['r'].append(a)
            else: d['w'].append(a)
        elif len(ops) == 1:
            if base in ('clr', 'st', 'sf', 'seq', 'sne', 'scc', 'scs', 'spl', 'smi'): d['w'].append(a)
            elif base in RMW: d['w'].append(a); d['r'].append(a)
            else: d['r'].append(a)
        else:
            d['r'].append(a)

def inited(a): return INIT[0] <= a < INIT[1]

if __name__ == '__main__':
    rows = []
    for off in sorted(info):
        d = info[off]
        wl = [x for x in d['w'] if not inited(x)]
        wi = [x for x in d['w'] if inited(x)]
        rl = d['r']
        cls = None
        if d['a']:
            continue
        if not rl and (wl or wi):
            cls = 'WRITTEN-NEVER-READ' + (' (init only)' if not wl else '')
        elif rl and not wl and not wi:
            cls = 'READ-NEVER-WRITTEN'
        elif rl and not wl and wi:
            cls = 'READ, init-only writer'
        if cls or '--all' in sys.argv:
            rows.append((off, cls, wl[:4], wi[:2], rl[:4]))
    for off, cls, wl, wi, rl in rows:
        print('%6d(A4) %-28s w=%s init=%s r=%s' % (off, cls, [hex(x) for x in wl], [hex(x) for x in wi], [hex(x) for x in rl]))
