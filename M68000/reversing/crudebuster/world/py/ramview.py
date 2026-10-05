"""ramview.py <ram.bin> : print flags, player records, pool records of a work RAM dump."""
import sys
d = open(sys.argv[1], "rb").read()
def hx(a, n): return " ".join("%02x" % d[a-0x80000+i] for i in range(n))
print("flags 80000:", hx(0x80000, 0x60))
print("scroll 80400:", hx(0x80400, 0x40))
print("P1:", hx(0x80100, 0x80))
for nm, base, stride, n in (("A",0x81000,0x40,16),("B",0x81400,0x40,32),("C",0x81c00,0x20,8)):
    for i in range(n):
        a = base + stride*i
        if d[a-0x80000] & 0x80: print(nm, i, hx(a, stride))
print("81e00:", hx(0x81e00, 0x40))
