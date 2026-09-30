"""Real chain for a cheat name: high-score name entry (cheat_entry.run) -> title -> fire -> world select -> fire -> level start.
Prints $bb7d, $bb74/$bb75 (health/max), $bb72 (weapon), $bb78 after $bb7e ran and after the level installed ($bbc8)."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from cheat_entry import *

def chain(name):
    r, res = run(name, verbose=False)
    out = {'name': name, 'bb7d': res['bb7d']}
    r.until(0x17ada, 30000000)          # title loop reached (IKBD bytes sent while the reload runs with interrupts masked are lost)
    r.cmd('s 30000')
    # title screen: fire -> $17b52 -> jsr $bb7e
    r.joy(FIRE)
    ok = r.until(0xbb7e, 30000000)
    out['bb7e_reached'] = ok
    r.until(0xbb88, 2000)
    r.cmd('s 40')
    r.until(0xbbc6, 4000)     # rts of the $bb7e block (after both cheat compares)
    out['after_bb7e'] = dict(score=r.l(0xbb6e), weapon=r.b(0xbb72), hp=r.b(0xbb74), hpmax=r.b(0xbb75), world=r.b(0xbb76), extra=r.b(0xbb78), mask=r.b(0xbb79))
    r.joy(0); r.until(0x17f52, 40000000)
    r.cmd('s 300000')
    # world select: hold fire to confirm the cursor's icon, loop until the level install ($bbc8)
    got = False
    for k in range(20):
        r.joy(FIRE); got = r.until(0xbbc8, 1500000); r.joy(0)
        if got: break
        r.cmd('s 300000')
    out['bbc8_reached'] = got
    if got:
        r.until(0xbbfc, 200)
        out['after_bbc8'] = dict(weapon=r.b(0xbb72), hp=r.b(0xbb74), hpmax=r.b(0xbb75), world=r.b(0xbb76), extra=r.b(0xbb78))
    r.snap(f'scratchpad/impossamole/agents/secrets/data/chain_{name.strip(".")}.snap')
    r.close()
    return out
if __name__ == '__main__':
    print(chain(sys.argv[1]))
