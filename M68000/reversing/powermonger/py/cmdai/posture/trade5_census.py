# Men per side in the $51b66 pool (511 x 50 B): live = byte6 $0e, dead = byte6 $0c (side negated in byte 5);
# plus the 12 traded men $53b6e + 50k: byte 44, health 45, side 5. Usage: census.py <ram>...
import sys
from collections import Counter
s8 = lambda b: b - 256 if b > 127 else b
for p in sys.argv[1:]:
    r = open(p, "rb").read()
    live, dead = Counter(), Counter()
    for k in range(511):
        o = r[0x51b66 + 50 * k:0x51b66 + 50 * k + 50]
        if o[6] == 0x0e: live[s8(o[5])] += 1
        elif o[6] == 0x0c: dead[-s8(o[5])] += 1
    men = [r[0x53b6e + 50 * k:0x53b6e + 50 * k + 50] for k in range(12)]
    print(p.split("/")[-1], "posture", r[0x51974:0x51976].hex(), "live", dict(sorted(live.items())), "dead", dict(sorted(dead.items())),
          "| 12: hp", " ".join(f"{m[45]:02x}" for m in men), "side", " ".join(f"{s8(m[5])}" for m in men))
