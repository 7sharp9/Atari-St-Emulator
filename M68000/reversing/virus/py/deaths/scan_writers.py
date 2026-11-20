"""Raw byte scan of a snapshot's RAM for absolute-long references to $62a5d / $62a5e (and the word $62a5c for .w stores)."""
import sys, os
p = os.path.abspath(os.path.dirname(__file__))
while not os.path.exists(os.path.join(p, 'tools', 'rdis.py')): p = os.path.dirname(p)
sys.path.insert(0, os.path.join(p, 'tools'))
import gfxview
ram, _ = gfxview.load_ram(sys.argv[1])
for tgt in (0x62a5c, 0x62a5d, 0x62a5e, 0x62a5f):
    pat = tgt.to_bytes(4, 'big'); i = 0
    while True:
        i = ram.find(pat, i)
        if i < 0: break
        if i < 0x30000: print(f'{tgt:x} @ {i-2:06x}: {ram[i-4:i+6].hex()}')
        i += 1
print('--- any absolute long in $62a40..$62a7f other than the four')
for i in range(0x400, 0x30000-4):
    v = int.from_bytes(ram[i:i+4], 'big')
    if 0x62a40 <= v <= 0x62a7f and v not in (0x62a5c,0x62a5d,0x62a5e,0x62a5f) and ram[i-2] in (0x41,0x43,0x45,0x47,0x49,0x4b,0x4d,0x4f,0x23,0x21,0x2b,0x2f,0x13,0x33,0x42,0x4a,0x4e) : print(f'{v:x} @ {i-2:06x}: {ram[i-4:i+6].hex()}')
