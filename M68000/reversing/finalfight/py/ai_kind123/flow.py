"""flow.py <lo> <hi> <entry>... : control-flow following listing of the 68000 program ROM in [lo,hi).
Reachable code is printed as instructions with labels; everything else in [lo,hi) is printed as .dw data.
Dispatch tables (move.w K(PC,Dn.w) == $T+Dn / jsr|jmp K(PC,Dm.w)) are resolved: count = word[T]/2, targets = T+word.
Calls out of [lo,hi) are listed but not followed.  Output: flow_<lo>_<hi>.txt under $AI123_OUT (default scratchpad/finalfight/p3/b/out) (or stdout with -)."""
import os, sys, os, re
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, '../../../..'))
sys.path.insert(0, os.path.join(root, 'tools'))
from disassemble import Disassembler
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
D = Disassembler(rom, 0)
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
entries = [int(x, 16) for x in sys.argv[3:]]
FORCED = {int(a, 16): int(b) for a, b in (kv.split(':') for kv in os.environ.get('FLOW_TABLES', '').split(',') if kv)}
code = {}      # addr -> (text, next)
labels = {}    # addr -> set of reasons
tables = {}    # T -> count
ext_calls = {}
work = list(entries)
for e in entries: labels.setdefault(e, set()).add('entry')
def rw(a): return (rom[a] << 8) | rom[a + 1]
TGT = re.compile(r'^(bra|bsr|b[a-z]{1,2}|jsr|jmp|dbf|db[a-z]{1,2})\b')
def targets(text):
    m = TGT.match(text)
    if not m or text.startswith('btst') or text.startswith('bset') or text.startswith('bclr') or text.startswith('bchg'): return []
    mn = m.group(1)
    if '(PC,' in text:
        m2 = re.search(r'== \$([0-9a-f]+)\+', text)
        if m2:
            T = int(m2.group(1), 16)
            return [('table', T)]
        return []
    m2 = re.search(r'== \$([0-9a-f]+)$', text)
    if m2: return [(mn, int(m2.group(1), 16))]
    m2 = re.search(r'\$([0-9a-f]+)(\.[wl])?$', text)
    if m2: return [(mn, int(m2.group(1), 16))]
    return []
while work:
    a = work.pop()
    while True:
        if a in code or a < lo or a >= hi: break
        try:
            text, nxt = D.decode_one(a)
        except Exception as ex:
            text, nxt = '<error %s>' % ex, a + 2
        code[a] = (text, nxt)
        if text.startswith('???') or text.startswith('<error'): break
        # dispatch idiom: table via move.w == $T+Dn
        m = re.search(r'== \$([0-9a-f]+)\+D\d', text)
        nt = D.decode_one(nxt)[0] if nxt < hi else ''
        def count_for(T):
            if T in FORCED: return FORCED[T]
            n = rw(T) // 2
            if rw(T) % 2 == 0 and rw(T) <= 128: return n
            # relaxed: the table is as long as the smallest positive entry (code follows it)
            mn = 1 << 30; i = 0
            while 2 * i < mn and i < 48:
                v = rw(T + 2 * i)
                if v < 0x8000 and v > 0: mn = min(mn, v)
                i += 1
            ok = all(lo <= T + (rw(T + 2 * k) if rw(T + 2 * k) < 0x8000 else rw(T + 2 * k) - 0x10000) < hi for k in range(i))
            return i if ok and i >= 2 else 0
        if m and text.startswith('move.w') and re.match(r'(jsr|jmp) -?\d+\(PC,D\d\.w\)', nt) and count_for(int(m.group(1), 16)):
            T = int(m.group(1), 16)
            if T not in tables:
                n = count_for(T)
                tables[T] = n
                for i in range(n):
                    v = rw(T + 2 * i); t = T + (v if v < 0x8000 else v - 0x10000)
                    labels.setdefault(t, set()).add('tbl%x[%d]' % (T, i))
                    work.append(t)
        for kind, t in targets(text):
            if kind == 'table': continue
            if t < lo or t >= hi:
                ext_calls.setdefault(t, 0); ext_calls[t] += 1
                continue
            labels.setdefault(t, set()).add(kind)
            work.append(t)
        mn = text.split()[0]
        if mn in ('rts', 'rte') or mn == 'bra' or (mn == 'jmp'):
            break
        a = nxt
out = []
a = lo
def ann(addr):
    r = labels.get(addr)
    return ''
while a < hi:
    if a in code:
        text, nxt = code[a]
        if a in labels:
            out.append('L%x:   ; %s' % (a, ','.join(sorted(labels[a]))))
        out.append('  %06x: %s' % (a, text))
        a = nxt
    else:
        # data run until next code address
        b = a
        while b < hi and b not in code: b += 2
        tag = ' ; table(%d)' % tables[a] if a in tables else ''
        i = a
        while i < b:
            j = min(i + 16, b)
            out.append('  %06x: .dw %s%s' % (i, ' '.join('%04x' % rw(k) for k in range(i, j, 2)), tag if i == a else ''))
            i = j
        a = b
res = '\n'.join(out) + '\n'
res += '; external calls: ' + ' '.join('%x(%d)' % (k, v) for k, v in sorted(ext_calls.items())) + '\n'
outdir = os.environ.get('AI123_OUT') or os.path.join(root, 'scratchpad/finalfight/p3/b/out')
os.makedirs(outdir, exist_ok=True)
dest = os.path.join(outdir, 'flow_%x_%x.txt' % (lo, hi))
open(dest, 'w').write(res)
print(dest, len(out), 'lines;', len(code), 'insns;', len(tables), 'tables')
