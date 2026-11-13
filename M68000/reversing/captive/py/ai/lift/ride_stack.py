"""Where the lift handler runs inside the frame: ride_stack.py <snap>. Presses keypad 1 ($6d), stops at $902e and
prints the longwords on the stack (candidate return addresses), then counts $88b8/$8912/$88d6 against $902e/$90e2
order by running to each in turn."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_input import srv, w16  # noqa
s = srv(sys.argv[1])
s('kbd', bytes=[0x6d])
r = s('run', max_steps=400000, until_pc=[0x902e])
sp = s.reg('a7')
st = s.read(sp, 64)
print('at', r.get('pc'), 'a7', hex(sp), 'stack longs', [hex(struct.unpack('>I', st[i:i + 4])[0]) for i in range(0, 64, 4)])
seq = []
for _ in range(4):
    r = s('run', max_steps=200000, until_pc=[0x88b8, 0x8912, 0x88d6, 0x90e2, 0x9116])
    seq.append((r.get('pc'), w16(s, 26), w16(s, 28))); s('step', n=1)
print('next arrivals (pc, party x, y):', seq)
s('kbd', bytes=[0xed]); s.close()
