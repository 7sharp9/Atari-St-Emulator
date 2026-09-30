"""hiscore_entry.py - drive the high-score initials entry ($172f0) live on a COPY of the disk (the game writes SSPRINT.HSC back).
From snap/prep_kbd.snap (keyboard player 0 = blue car, in the prepare screen): stop at $172f0, poke player 0's 6 score digits to 999990
(rank 1), then enter initials with the keyboard channel: D = right (next letter), A = left (previous), LShift = fire (accept).
Reads the resulting stored initials (glyph code = letter+0xb) at -8050(A4)+3*rank and the score digits -7956(A4)+6*rank."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
DISK = os.path.join(TMP, 'copy.ST')
r = R(os.path.join(AGENT, 'snap', 'prep_kbd.snap'), disk=DISK)
out, g = r.cmd('u 172f0 60000000'); print(out[1].strip())
before = r.mem(sscfg.A4 - 8050, 93)
r.cmd('w 1d856 09090909'); r.cmd('w 1d85a 09000000')
f1 = r.g16(-3912); print('flags before', [r.g16(-3914 + 2*i) for i in range(4)])
r.cmd('w %x 0001%04x' % (sscfg.A4 - 3914, f1))      # player 0 flag -> 1 (nonzero = eligible for the score check at $17346)
print('flags after', [r.g16(-3914 + 2*i) for i in range(4)])
print('score digits now', r.mem(sscfg.A4 - 4846, 6).hex(' '))
a = Acc(r, [0x17678, 0x16766, 0x17a32, 0x17eb8, 0x17d00, 0x17dba, 0x1000e, 0x13a5e])
a.run(1500000); a.show('entered')
# choose letters: first letter: right x3 (A->D), second: left x2 (A->Z->Y  i.e. wrap), third: nothing
def key(code, hold=300000, gap=300000):   # the loop polls one player per 2 frames, round robin over 3 players
    a.kbd('%02x' % code); a.run(hold); a.kbd('%02x' % (code | 0x80)); a.run(gap)
r.cmd('snap %s' % os.path.join(AGENT, 'snap', 'hiscore_entry.snap'))
for _ in range(3): key(0x20)        # D = right
key(0x2a)                            # LShift fire: accept letter 1
for _ in range(2): key(0x1e)        # A = left  (A -> blank(27) -> Z(26))
key(0x2a)                            # accept letter 2
key(0x2a)                            # accept letter 3 (A)
a.run(3000000)
after = r.mem(sscfg.A4 - 8050, 93)
print('initial table before/after (first 12 bytes):', before[:12].hex(' '), '|', after[:12].hex(' '))
print('diff positions', [i for i in range(93) if before[i] != after[i]])
sc = r.mem(sscfg.A4 - 7956, 186)
print('score row 0..2:', sc[:18].hex(' '))
a.show('after entry'); 
r.close()
