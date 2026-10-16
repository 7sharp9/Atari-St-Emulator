"""bottle_throw.py SNAP MODE [hold] [settle]: MODE fire = FIRE held `hold` steps then released (throws the selected item), control = no input, same budget.
hits on the push sites over the whole window (started before the press), then 465/508 records, VAR 10, room lists. MODE bp = stop at $f69c and print the ring entry."""
import sys, os
d = os.path.abspath(os.path.dirname(__file__))
while not os.path.exists(d + '/tools/rdis.py'): d = os.path.dirname(d)
ROOT = os.environ.get('M68000_ROOT', d); snap = os.path.abspath(sys.argv[1]); mode = sys.argv[2]
HOLD = int(sys.argv[3]) if len(sys.argv) > 3 else 200000; settle = int(sys.argv[4]) if len(sys.argv) > 4 else 1500000
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/action/exit_level0/g2')
from lib import *
SITES = [0xf69c, 0xfe24, 0xa184, 0xa486, 0xfa62, 0xf328]
def rec(r, oid):
    a = live_rec(r, oid)
    return None if a is None else dict(addr=hex(a), x=r.b(a), y=r.b(a + 1), z=r.b(a + 2), b3=hex(r.b(a + 3)), room=r.b(a + 10), b15=hex(r.b(a + 15)))
def roomlist(r, room):
    row = r.l(A5 + 96) + 0x12 * 5; idx, dat = r.l(row), r.l(row + 4); e = r.l(idx + 4 * room)
    if (e >> 16) == 0: return None
    a = dat + (e & 0x1ffff); n = e >> 16
    return [r.w(a + 2 * i) for i in range(n // 2)]
def show(r, tag):
    print(tag, st(r), 'ruck', slot_ids(r), 'sel1236', r.w(A5 + 1236))
    print('  465', rec(r, 465)); print('  508', rec(r, 508)); print('  VAR10', r.b(A5 + 2282 + 10), 'XP', r.l(A5 + 1192))
    print('  room86 list', roomlist(r, 86)); print('  room84 list', roomlist(r, 84))
    e = ent(r, 508); print('  508 placement entry in loaded room', e)
r = Repl(snap); show(r, 'before')
if mode == 'bp':
    joy(r, FIRE); o = r.cmd('bp f69c %d' % HOLD); joy(r, 0)
    o += r.cmd('bp f69c %d' % settle)
    print([l for l in o if 'break' in l.lower()][:4])
    wp = r.l(A5 + 304); ent8 = bytes(r.mem(wp - 8, 8)); p = int.from_bytes(ent8[2:6], 'big')
    print('ring entry at wp-8:', ent8.hex(' '), 'event', int.from_bytes(ent8[:2], 'big'), 'record $%x id %d' % (p, r.w(p + 4)), 'word', int.from_bytes(ent8[6:8], 'big'))
    print('  465 rec now', rec(r, 465))
    r.cmd('s 400000'); show(r, 'after bp+400000')
else:
    if mode == 'fire': joy(r, FIRE)
    try:
        h1 = r.hits(HOLD, *SITES)
    except Exception:
        import time; time.sleep(1); print('ERR', r.err[-15:]); raise
    joy(r, 0)
    h2 = r.hits(settle, *SITES)
    print('hits hold', {'%x' % k: v for k, v in h1.items()}, 'settle', {'%x' % k: v for k, v in h2.items()})
    show(r, 'after')
    if len(sys.argv) > 5: r.snap(os.path.abspath(sys.argv[5]))
r.close()
