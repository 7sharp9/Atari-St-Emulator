"""reset_picture.py - python port of the RLE picture decoder $10236 (used by the RESET hook $10430 and, via $146b8, for the
credits page): marker word = first word; run = marker,value,count; 4 planes x 4000 words, interleaved dest word k*4+plane.
Reads source ptr -126(A4) and palette -5460(A4) from the attract snapshot; writes reset_picture.png and compares the decode
against the live screen written by `callcap 10236` (match count = pixels equal)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shot import *
r = R(sscfg.SNAP_ATTRACT)
src = r.g32(-126)
pal = r.mem(sscfg.A4 - 5460, 32)
blob = r.mem(src, 0x10000)
words = [int.from_bytes(blob[i:i+2], 'big') for i in range(0, len(blob), 2)]
marker = words[0]; i = 1
dest = [0] * 16000
for plane in range(4):
    k = 0
    while k < 4000:
        w = words[i]
        if w == marker:
            val, cnt = words[i+1], words[i+2]; i += 3
            for _ in range(cnt):
                dest[k*4 + plane] = val; k += 1
        else:
            dest[k*4 + plane] = w; i += 1; k += 1
print('consumed words', i, 'marker %04x' % marker, 'src %x' % src)
scr = b''.join(w.to_bytes(2, 'big') for w in dest)
img, _ = grab(r, base=0, pal=pal) if False else (None, None)
from shot import Image
P = []
for n in range(16):
    w = int.from_bytes(pal[2*n:2*n+2], 'big')
    P.append(tuple(((w >> s) & 7) * 255 // 7 for s in (8, 4, 0)))
img = Image.new('RGB', (320, 200)); px = img.load()
for y in range(200):
    for xb in range(20):
        o = y * 160 + xb * 8
        ws = [int.from_bytes(scr[o + 2*p:o + 2*p + 2], 'big') for p in range(4)]
        for b in range(16):
            v = 0
            for p in range(4): v |= ((ws[p] >> (15 - b)) & 1) << p
            px[xb * 16 + b, y] = P[v]
img.resize((640, 400), Image.NEAREST).save(os.path.join(AGENT, 'reset_picture.png'))
# verify against the emulator: run the real routine and compare the screen buffer it filled ([-82(A4)] = $f8000)
out, g = r.cmd('callcap 10236 30000000 %s' % os.path.join(AGENT, 'tmp', 'cc10236.json'))
import json
j = json.load(open(os.path.join(AGENT, 'tmp', 'cc10236.json')))
live = {}
for a, old, new in j['mem']:
    live[a] = new
base = r.g32(-82)
ok = tot = 0
for k in range(32000):
    a = base + k
    if a in live:
        tot += 1; ok += (live[a] == scr[k])
print('bytes the real routine wrote into screen', tot, 'matching my decode', ok)
r.close()
