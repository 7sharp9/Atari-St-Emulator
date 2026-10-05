"""chain.py <dump>...: the attack chain roll $406f2: at the end of (+3,+4,+5) = (2,2,8,2) ($3df92) it tests bit (rnd & $1f) of the long at $3edea[level*4] (+128 when 148 = 1; $3eeea for two players);
set: another attack (next state (2,2,0,0)), clear: back to idle ($3dfae). Counts the observed outcomes against the ROM bit density popcount/32 at the levels seen."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dd import *
root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
exp = 0.0; n = 0; chained = 0; rows = []
for path in sys.argv[1:]:
    D = Dump(path)
    for i in range(1, D.n - 1):
        if not D.u8(i, BOSS): continue
        cur = (D.u8(i, BOSS + 3), D.u8(i, BOSS + 4), D.u8(i, BOSS + 5)); prv = (D.u8(i - 1, BOSS + 3), D.u8(i - 1, BOSS + 4), D.u8(i - 1, BOSS + 5))
        if prv == (2, 8, 2) and cur != (2, 8, 2) and D.u8(i - 1, BOSS + 2) == 2:
            lvl = D.u8(i - 1, BOSS + 96); ang = D.u8(i - 1, BOSS + 148)
            base = (0x3eeea if D.u8(i - 1, BOSS + 163) == 3 else 0x3edea) + (128 if ang else 0) + 4 * lvl
            m = int.from_bytes(rom[base:base + 4], 'big'); p = bin(m).count('1') / 32
            n += 1; exp += p
            if cur[0] == 2 and cur[1] in (0, 2) and cur[2] == 0: chained += 1; rows.append((1, lvl, ang, p))
            else: rows.append((0, lvl, ang, p))
print('chain decisions %d: observed chained %d, expected %.1f (sum of popcount/32 at the level and angry flag of each)' % (n, chained, exp))
