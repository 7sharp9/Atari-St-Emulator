"""mapdump_dead.py - run the UNREFERENCED routine $155ce (never called by anything) on the live race snapshot with callcap and
render what it draws: it blits the 40x25 byte map at [-1910(A4)] (the surface/collision map) into the back screen [-78(A4)]
(each map byte is replicated over the 4 bitplanes x 4 scanlines; 8-row pitch)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shot import *
r = R(sscfg.SNAP_RACE)
mp = r.g32(-1910); scr = r.g32(-78)
print('map ptr %x  back screen %x' % (mp, scr))
mapb = r.mem(mp, 1000)
out, g = r.cmd('callcap 155ce 2000000 %s' % os.path.join(AGENT, 'tmp', 'cc155ce.json'))
print(out[1].strip())
j = json.load(open(os.path.join(AGENT, 'tmp', 'cc155ce.json')))
delta = {a: n for a, o, n in j['mem']}
pal = r.mem(0xffff8240, 32)
cur = bytearray(r.mem(scr, 32000))
touched = 0
for a, n in delta.items():
    if scr <= a < scr + 32000: cur[a - scr] = n; touched += 1
print('bytes written into the back screen:', touched)
# check: each written byte equals a map byte replicated
# render
P = []
for i in range(16):
    w = int.from_bytes(pal[2*i:2*i+2], 'big'); P.append(tuple(((w >> s) & 7) * 255 // 7 for s in (8, 4, 0)))
img = Image.new('RGB', (320, 200)); px = img.load()
for y in range(200):
    for xb in range(20):
        o = y * 160 + xb * 8
        ws = [int.from_bytes(cur[o + 2*p:o + 2*p + 2], 'big') for p in range(4)]
        for b in range(16):
            v = 0
            for p in range(4): v |= ((ws[p] >> (15 - b)) & 1) << p
            px[xb * 16 + b, y] = P[v]
img.resize((640, 400), Image.NEAREST).save(os.path.join(AGENT, 'dead_155ce_map.png'))
# also plain render of the map bytes as 1bpp 320x25
m = Image.new('L', (320, 25)); mpx = m.load()
for y in range(25):
    for x in range(40):
        for b in range(8): mpx[x*8+b, y] = 255 if (mapb[y*40+x] >> (7-b)) & 1 else 0
m.resize((960, 75), Image.NEAREST).save(os.path.join(AGENT, 'surface_map_bits.png'))
print('map nonzero bytes', sum(1 for x in mapb if x), 'distinct values', sorted(set(mapb))[:20])
r.close()
