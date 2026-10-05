import sys; sys.path.insert(0, __import__("os").path.dirname(__file__))
from cbrom import *
from collections import Counter, defaultdict
Bt = [L(0x10558 + 4*i) for i in range(84)]
Ct = [L(0x106c8 + 4*i) for i in range(44)]
At = [L(0x10418 + 4*i) for i in range(80)]
print("pool B handlers"); 
for i,h in enumerate(Bt): print(i, hex(h), end="; ")
print("\npool C handlers")
for i,h in enumerate(Ct): print(i, hex(h), end="; ")
print()
for name, base in (("A",0x6c000),("B",0x6d000)):
    print("list", name)
    for lv in range(6):
        p = L(base+4*lv); c = Counter(); 
        while W(p) != 0xffff:
            c[B(p+2)&0x7f] += 1; p += 8
        print(lv, hex(L(base+4*lv)), dict(sorted(c.items())))
