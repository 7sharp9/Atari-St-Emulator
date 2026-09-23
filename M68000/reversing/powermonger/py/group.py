"""group.py <ram> [settl]: the selected group ($57fd2): state, men, food, posture, carried goods, its lead and roster, food piles; with `settl` every $4f916 settlement. strategy.md "What each order does"."""
import struct, sys
R = open(sys.argv[1], 'rb').read()
w = lambda a: struct.unpack('>H', R[a:a+2])[0]
sw = lambda a: struct.unpack('>h', R[a:a+2])[0]
g = w(0x57fd2); A = 0x51538 + g
lead = 0x51b66 + w(A-12)
cell = lambda c: (c & 63, (c >> 6) & 127)
print(f"grp {g:#x} state {w(A)} men(-24) {w(A-24)} first(-36) {w(A-36):#x} -48 {sw(A-48)} tgt24 {w(A+24):#x} "
      f"food(36) {w(A+36)} posture(60) {w(A+60)} carrying(84) {[w(A+84+12*i) for i in range(8)]}")
x, y = sw(lead+8), sw(lead+10)
print(f" lead {w(A-12):#x} cell ({x>>8},{y>>8}) b5 {R[lead+5]} b6 {R[lead+6]:#x} b7 {R[lead+7]:#x} mode {R[lead+31]:#x} prev {R[lead+30]:#x} "
      f"tgt ({R[lead+20]},{R[lead+22]}) b33 {R[lead+33]} b44 {R[lead+44]} b45 {R[lead+45]} f36 {w(lead+36):#x}")
# roster
o = w(A-36); n = 0; roster = []
while o and n < 200:
    r = 0x51b66 + o; roster.append((R[r+31], R[r+44], R[r+45])); o = w(r+26); n += 1
from collections import Counter
print(f" roster {n}: modes {dict(Counter(m for m,_,_ in roster))} b44 {dict(Counter(b for _,b,_ in roster))}")
if len(sys.argv) > 2:
    for i in range(0, 200):
        s = 0x4f916 + 18*i
        if w(s+14) == 0 and R[s+5] == 0 and w(s+12) == 0: continue
        lo = w(s+14)
        print(f" settl {i:3d} @{s:#x} owner {R[s+5]} cat {R[s+6]:#x} kind {R[s+7]} cell {cell(w(s+12))} lord {lo//32}")
# small-object piles $4bb4e (28-byte)
for a in range(0x4bb4e, 0x4bdee, 28):
    if R[a+6] not in (0, 0xff) and R[a+6] < 0x80:
        print(f" pile @{a:#x} b6 {R[a+6]:#x} cell {cell(w(a+8))} w10 {w(a+10)} goods {[w(a+12+2*i) for i in range(8)]}")
