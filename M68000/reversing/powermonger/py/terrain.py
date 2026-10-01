"""pm129: print the $438ee colour plane A (colour 0 = open sea, ai.md $1648e; the file name keeps the old 'terrain-type' reading) for a cell window,
marking own/foreign entities. Usage: terrain.py <ram> x0 x1 y0 y1"""
import struct, sys
R = open(sys.argv[1], 'rb').read()
x0, x1, y0, y1 = map(int, sys.argv[2:6])
sw = lambda a: struct.unpack('>h', R[a:a+2])[0]
loc = struct.unpack('>H', R[0x57ffe:0x58000])[0]
ent = {}
for i in range(1, 511):
    a = 0x51b66 + 50*i
    o = struct.unpack('>b', R[a+5:a+6])[0]
    if o: ent.setdefault((sw(a+8)>>8, sw(a+10)>>8), []).append(o)
print("     " + "".join(f"{x:3d}" for x in range(x0, x1+1)))
for y in range(y0, y1+1):
    row = ""
    for x in range(x0, x1+1):
        t = R[0x438ee + y*64 + x]
        row += f"{t:2x}" + ("*" if (x, y) in ent else " ")
    print(f"{y:3d}: {row}")
