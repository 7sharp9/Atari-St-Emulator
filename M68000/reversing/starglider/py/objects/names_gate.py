"""Gate: the type byte -> database name mapping.  The 'I' (Interrogate) screen of the docked ship ($d5d0) walks 17 entries;
for each it loads the type word from the table at $d724 (word per entry) and draws that type's wireframe with the same
routine $f6a8 that draws live objects ($10028, D0 = 0(A4)), with the entry's name from the pointer table at $d7d8.
This script docks the ship (poke 714(A6) = $ff on g_game1), presses I and then SPACE 17 times in the REPL; at every
breakpoint on $f6a8 it reads D0 (the type drawn) and A3 (the name pointer register of the interrogate screen) and checks
them against the static tables.  A second check stops the first $f6a8 calls of ordinary flight (no poke) and compares D0
with the types of the in-view list 148(A6).
    python3 reversing/starglider/py/objects/names_gate.py     -> 'names 17/17', 'view 4/4'"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objlib as ol
from objlib import A6, Mem

def strat(m, a):
    e = m.b.index(0, a); return bytes(m.b[a:e]).decode('latin1')

def main():
    snap = ol.sg.SNAP_GAME1
    m = Mem(ol.sg.load_ram(snap))
    exp = []
    for i in range(1, 18):
        exp.append((m.rw(0xd724 + 2 * i), strat(m, m.rl(0xd7d8 + 4 * i)), m.rl(0xd7d8 + 4 * i)))
    lines = ['wb %x ff' % (A6 + 714), 'kbd 17', 's 120000', 'kbd 97', 'bp f6a8 600000', 'r']
    for i in range(16):
        lines += ['kbd 39', 's 60000', 'kbd b9', 'bp f6a8 600000', 'r']
    out = ol.repl_run(snap, lines)
    got = re.findall(r'breakpoint \$0000f6a8 hit.*?D0:([0-9a-f]{8}).*?A3:([0-9a-f]{8})', out, re.S)
    print(' bp hits at $f6a8:', len(got))
    ok = 0
    for (d0, a3), (t, name, ptr) in zip(got, exp):
        good = int(d0, 16) == t and int(a3, 16) == ptr
        ok += good
        print('  entry type %2d  D0=%d  A3=%x  -> %s %s' % (t, int(d0, 16), int(a3, 16), name, 'ok' if good else 'MISMATCH'))
    print('names %d/17' % ok)
    # live view
    cnt = m.rws(A6 + 574); A5 = m.rl(A6 + 148)
    types = [m.rw(m.rl(A5 + 4 * i)) for i in range(cnt)]
    out = ol.repl_run(snap, ['bp f6a8 400000', 'r'] + ['bp f6a8 400000', 'r'] * (cnt - 1))
    got = [int(x, 16) for x in re.findall(r'breakpoint \$0000f6a8 hit.*?D0:([0-9a-f]{8})', out, re.S)]
    print(' in-view list types (148(A6)):', types, ' D0 at the first %d f6a8 calls:' % cnt, got)
    print('view %d/%d' % (sum(a == b for a, b in zip(sorted(types), sorted(got))), cnt))
main()
