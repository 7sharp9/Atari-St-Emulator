"""brief1.py - from the lord screen, click to continue and stop at the conquest briefing wait ($1afc4)."""
import sys
from eg import *
from popdrive import click_lines
tag = sys.argv[1] if len(sys.argv) > 1 else 'win'
src = OUT + '/%s_lord.snap' % tag
m = ram(src)
L = click_lines(sw(m, 0x24748), sw(m, 0x2474a), 160, 150)
L = L[:-1] + ['bp 1afc4 80000000', 'snap %s/%s_brief.snap' % (OUT, tag), 'r']
out = repl(src, L)
r = regs(out)
print('\n'.join(x for x in out.splitlines() if x.startswith('PC') or 'saved' in x))
m = ram(OUT + '/%s_brief.snap' % tag)
a6 = r['A6']
for off in (-72, -118):
    b = a6 + off; print(off, sw(m, b), sw(m, b + 2), sw(m, b + 4), cstr(m, b + 6))
print('world', w(m, WORLD), 'name', cstr(m, 0x37e86), 'rec', m[0x22ad8:0x22ae2].hex(), '-18', sw(m, a6 - 18))
