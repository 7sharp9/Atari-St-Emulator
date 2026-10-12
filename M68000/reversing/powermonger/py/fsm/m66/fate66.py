#!/usr/bin/env python3
"""fate66.py <watch>...: for every record that $5106 stamps prev $66, print its later filtered WATCH writes
(mode/prev writes at $14fdc, $161f0, $14c66, $14e44, ...). Record = (addr-$51b66)//50, offset = remainder."""
import sys, re
for fn in sys.argv[1:]:
    print('==', fn)
    st = set()
    for l in open(fn):
        m = re.search(r'step=(\d+) pc=\$(\w+) Write(\w+) \$(\w+) <- \$(\w+)', l)
        if not m: continue
        s, pc, w, a, v = m.groups(); a = int(a, 16); r, off = divmod(a - 0x51b66, 50)
        if pc == '005106': st.add(r)
        if r in st: print(s, pc, w, 'rec', r, 'off', off, v)
