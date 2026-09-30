"""OOCHOUCH ($bb7d=5): hazard-tile (water) damage.  From hop3/snaps/seg5_stone_hole.snap (start of the four pits) hold RIGHT with $bb7d = 0 and = 5.
Per 100,000-step chunk: hits of $eba2 (the hazard-damage branch of $eafa, tile category 9 under the foot sensors $227e8/$227e9), and the
number of chunks that end with a foot sensor reading category 9 (hero standing in/over water).  Health is poked full at each chunk start
(labelled), so the run is not ended by enemy contacts.  $bb7d is set with a longword write at $bb7a (neighbours read first, written back)."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
SNAP = 'scratchpad/impossamole/agents/hop3/snaps/seg5_stone_hole.snap'
def trial(cheat, steps=6000000, bits=0x08):
    r = Repl(SNAP)
    nb = r.mem(0xbb7a, 3)
    r.cmd('w bb7a %s%02x' % (nb.hex(), cheat))
    assert r.b(0xbb7d) == cheat
    r.joy(bits)
    water_hits = 0; on_water_chunks = 0; lost = 0
    for i in range(steps // 100000):
        r.cmd('w bb74 12120300')
        out = r.cmd('hits 100000 eba2 eb32 eb5a')
        n = {l.split()[0]: int(l.split()[1]) for l in out if l.startswith('  $')}
        water_hits += n['$00eba2']
        s = r.mem(0x227e8, 2)
        if 9 in [r.b(0x25000 + t) for t in s]: on_water_chunks += 1
        lost += 18 - r.b(0xbb74)
    st = r.mem(0x1a572, 8)
    r.close()
    return dict(cheat=cheat, eba2_hits=water_hits, chunks_with_foot_sensor_9=on_water_chunks, hp_lost_sum=lost, last_hero=st.hex())
if __name__ == '__main__':
    for c in (0, 5):
        print(trial(c))

def frames_on_hazard(cheat, steps=6000000, bits=0x08):
    """At every execution of $eb2e (the cheat-5 compare; only reached in hero states 0/1 with no hit cooldown) read the foot sensors: how many frames had category 9 under a foot."""
    r = Repl(SNAP)
    nb = r.mem(0xbb7a, 3)
    r.cmd('w bb7a %s%02x' % (nb.hex(), cheat))
    r.joy(bits)
    used = 0; n_at = 0; on9 = 0; eba2 = 0
    while used < steps:
        r.cmd('w bb74 12120300')
        out = r.cmd('bp eb26 100000')
        if not any('breakpoint' in l and ' hit ' in l for l in out):
            used += 100000; continue
        got = int([l for l in out if 'breakpoint' in l][0].split('after ')[1].split()[0])
        used += got; n_at += 1
        s = r.mem(0x227e8, 2)
        if 9 in [r.b(0x25000 + t) for t in s]: on9 += 1      # sensors hold tile ids; $be96 maps them through the table at $25000
        r.cmd('s 1')
    r.close()
    return dict(cheat=cheat, frames_reaching_eb26=n_at, of_which_foot_sensor_is_9=on9)
if __name__ == '__main__':
    for c in (0, 5):
        print(frames_on_hazard(c))
