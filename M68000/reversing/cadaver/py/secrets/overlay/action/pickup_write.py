"""pickup_write.py: pick up the PICKAXE (id 168) through the icon panel (fire near it, choose icon 2 = take) with `watch` on (a) the type-8 data
records, (b) the type-8 index words, (c) the rucksack count byte 2438(A5).  Prints every write (pc, addr, value).  Start: sv_pick.snap (right, up, right, down from gameplay_empire.snap)."""
from drv import *
SNAP = ensure('pick')
def run(what, addr, ln):
    r = Repl(SNAP); t = Tally(r)
    d = type8(r)
    open_panel(r, t)
    r.err.clear(); r.cmd(f'watch {addr:x} {ln}')
    pick_icon_id(r, t, 2)
    lines = [l for l in r.err if l.startswith('WATCH')]
    print(f'== {what} watch ${addr:x}+{ln}: {len(lines)} writes'); [print('  ', l) for l in lines[:20]]
    print('   type8 after:', type8(r))
    r.close(); return d
d = type8(Repl(SNAP)) if False else None
r = Repl(SNAP); d = type8(r); print('type-8 descriptor', d); r.close()
data, idx = int(d['data'], 16), int(d['index'], 16)
run('data records', data, 16)
run('index words', idx, 16)
run('count byte 2438(A5)', A5 + 2438, 1)
