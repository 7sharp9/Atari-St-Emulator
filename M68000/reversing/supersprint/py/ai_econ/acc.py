"""acc.py <off> ... : classify every indexed access to array -N(A4) as R/W by the first (An)-operand
instruction after the `lea -N(A4),An`, with the containing function.  Heuristic (dest operand = W).
Direct (non-lea) uses are printed too.  Every W site must still be read to its end by hand."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refs as R

def classify(ins, st, off):
    pat = re.compile(r'lea %d\(A4\),(A\d)' % off)
    direct = re.compile(r'(?<![\d-])%d\(A4\)' % off)
    for i, (a, t) in enumerate(ins):
        m = pat.search(t)
        if m:
            reg = m.group(1)
            for j in range(i + 1, min(i + 8, len(ins))):
                tt = ins[j][1]
                if tt.startswith('adda'):
                    continue
                if '(' + reg + ')' in tt:
                    dest = re.search(r',\s*\(?%s\)?\+?$' % reg, tt) is not None
                    w = (dest and not tt.startswith(('cmp', 'tst', 'btst'))) or tt.startswith(('clr', 'addq', 'subq', 'neg', 'not'))
                    print('  $%06x [fn $%06x] %s  %s' % (ins[j][0], R.func_of(st, a) or 0, 'W' if w else 'R', tt))
                    break
            else:
                print('  $%06x [fn $%06x] ?  %s (no (%s) use within 8)' % (a, R.func_of(st, a) or 0, t, reg))
        elif direct.search(t):
            print('  $%06x [fn $%06x] D  %s' % (a, R.func_of(st, a) or 0, t))

if __name__ == '__main__':
    ins = R.load(); st = R.funcs(ins)
    for off in sys.argv[1:]:
        print('== %s(A4)' % off)
        classify(ins, st, int(off))
