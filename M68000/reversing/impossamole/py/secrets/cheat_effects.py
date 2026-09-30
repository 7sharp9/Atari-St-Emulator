"""Live effects of cheats 3, 4 and 6 from the Amazon gameplay snapshot (health 11 of 18, world 3).  Every poke is a longword write whose
neighbours are read first and written back.
 6 JUGGLERS: callcap of the heal-pickup handler $12e7e with health 1: gain 4+world (7) without the cheat, 14 with it.
 4 ANNFRANK: health forced to 0 with $bb78 = 1: revive at max/2 ($ec50) and $bb78 cleared, no Game Over ($17fe8 not reached in 6M steps);
            control $bb78 = 0: Game Over reached.
 3 COMMANDO: special weapon active ($227fa = 1, $227fb = 30 units, $227fc = 0): after 3M steps $227fb is still 30 with the cheat, 28 without."""
import sys, re
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
SNAP = 'scratchpad/impossamole/agents/unpoked/s11/seg11_shaft_exit.snap'
def setb(r, addr, val):
    base = addr & ~3
    b = bytearray(r.mem(base, 4)); b[addr - base] = val
    r.cmd('w %x %s' % (base, b.hex()))
    assert r.b(addr) == val, (hex(addr), r.b(addr), val)

def heal(cheat):
    r = Repl(SNAP)
    setb(r, 0xbb7d, cheat); setb(r, 0xbb74, 1)
    out = r.cmd('callcap 12e7e 200000')
    hp = [l for l in out if l.startswith('mem $00bb74')]
    r.close(); return hp

def revive(flag):
    r = Repl(SNAP)
    setb(r, 0xbb78, flag); setb(r, 0xbb74, 0)
    reached = r.until(0x17fe8, 6000000)
    res = dict(bb78_before=flag, game_over_reached=reached, hp=r.b(0xbb74), bb78_after=r.b(0xbb78), max=r.b(0xbb75))
    if not reached:
        r.cmd('s 300000'); res['hp_later'] = r.b(0xbb74)
    r.close(); return res

def special(cheat):
    r = Repl(SNAP)
    setb(r, 0xbb7d, cheat)
    setb(r, 0x227fa, 1); setb(r, 0x227fb, 30); setb(r, 0x227fc, 0)
    r.cmd('s 3000000')
    v = (r.b(0x227fa), r.b(0x227fb), r.b(0x227fc))
    r.close(); return v

if __name__ == '__main__':
    print('heal  cheat0', heal(0)); print('heal  cheat6', heal(6))
    print('revive bb78=1', revive(1)); print('revive bb78=0', revive(0))
    print('special cheat0 (227fa,227fb,227fc)', special(0)); print('special cheat3', special(3))
