"""radio_setup.py: from d_team.snap, blow up the enemy's three held Radio Stations (nodes 60, 70, 81) with the game's
own blast code (`$41f6..$4272`, then the clear `$429e..$42c4`), run in stserver with Stark (14) as the saboteur, and
save rad_team.snap with the CPU state, the current character, Stark's +52 and the live Morale restored.
Labelled pokes: 96(A6) = 14, Stark +52 = each site, bit 6 (a charge) on each Radio Station's building byte."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); root = HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')): root = os.path.dirname(root)
sys.path.insert(0, os.path.join(root, 'tools'))
from stclient import StServer
DISK = os.path.join(root, 'scratchpad', 'midwinter', 'zuul067.st')
SITES = {60: 0x2a46c, 70: 0x2a4ee, 81: 0x2a580}
STARK = 0x2b194 + 14 * 0x4a
s = StServer(root)
s('load', snapshot=os.path.join(root, 'scratchpad', 'midwinter', 'd_team.snap'), disk=DISK)
regs = s('regs')
keep = {a: s.read(a, n) for a, n in ((0x2c3d6, 2), (STARK + 52, 4), (0x2553c, 2))}
s('poke', addr=0x2c3d6, width=2, value=14)
for node, a in SITES.items():
    b = s.read(a + 6, 1)[0]
    assert b & 0x1f == 0xe and s.read(a, 1)[0] & 0x80, (node, hex(b))
    s('poke', addr=STARK + 52, width=4, value=a)
    s('poke', addr=a + 6, width=1, value=b | 0x40)
    s.call(0x41f6, stops=[0x4272])
    s.call(0x429e, stops=[0x42c4])
    print('node', node, 'building byte %02x -> %02x' % (b, s.read(a + 6, 1)[0]))
for a, v in keep.items():
    s('poke', addr=a, width=len(v), value=int.from_bytes(v, 'big'))
for name in ('usp', 'ssp', 'sr', 'a7', 'd0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2', 'a3', 'a4',
             'a5', 'a6', 'pc'):
    s('set_reg', name=name, value=int(str(regs[name]).lstrip('$'), 16))
after = s('regs')
assert all(after[k] == regs[k] for k in regs if k not in ('step',)), (regs, after)
print('2c188', s.read(0x2c188, 17).hex())
s('save', path=os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(root, 'scratchpad', 'midwinter', 'sabotage', 'rad_team.snap'))
s('shutdown')
