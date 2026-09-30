"""SPACE key (scancode $39, $ed52-$ed6e): dispatch to the per-world routine $ee16[world]; count the live enemy slots ($1a5de.., 5 x 108 bytes,
type word at +0) before and after, with and without the key, from three Amazon snapshots.  103(A0) is the gate ($ee9a: skip if 0 or $fe)."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
from hidden_keys import key
A = 'scratchpad/impossamole/agents/'
SNAPS = [A + 'hop3/snaps/seg5_stone_hole.snap', A + 'hop3/snaps/seg7_pillars.snap', A + 'hop3/snaps/seg9_ladder_corridor.snap', A + 'hop3/snaps/seg1_pillar_totem.snap']
def slots(r):
    out = []
    for i in range(5):
        b = r.mem(0x1a5de + 108 * i, 108)
        out.append(dict(i=i + 1, type=int.from_bytes(b[0:2], 'big'), x=int.from_bytes(b[2:4], 'big'), y=int.from_bytes(b[4:6], 'big', signed=True),
                        b100=b[100], dying=b[101], b102=b[102], gate103=b[103], anim=hex(int.from_bytes(b[22:26], 'big'))))
    return out
def run(snap, press):
    r = Repl(snap); r.cmd('s 30000')
    before = [s for s in slots(r) if s['type']]
    if press: key(r, 0x39, hold=60000)
    r.cmd('s 700000')
    after = [s for s in slots(r) if s['type']]
    d = dict(z227ff=r.b(0x227ff), z22800=r.b(0x22800), hp=r.b(0xbb74))
    r.close()
    return before, after, d
for sn in SNAPS:
    for press in (False, True):
        b, a, d = run(sn, press)
        print(sn.split('/')[-1], 'SPACE' if press else 'control', '| live enemy slots before', len(b), 'after 700k steps', len(a), d)
        if press:
            for s in b: print('    before', s)
            for s in a: print('    after ', s)
