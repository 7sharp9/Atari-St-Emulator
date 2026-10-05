#!/usr/bin/env python3
"""Parse the Final Fight stage scripts ($5aea/$5b4e/$5dfe/$5e36) and list the spawn entries.
Table $5f5e (1 player) / $5f7e (2 players): long per stage -> word offsets per area -> script.
Stream: [mode word] then repeated: trigger word D2 (negative = command: 8000 [mode], 8002 pause,
8004 [long] jump) else header [w16 w12 w18 flagw long24] then 16-byte entries
[delay, countflag, x, y, tag, kind, +20, +21, b54, b98, b96, b15] until a negative delay word, which is the end
command (8000, 8002 = another header follows, 8004 stage end, 8006, 8008, 800a).
usage: scripts.py [tag kind]   (filters)"""
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
rom = open(os.path.join(ROOT, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
w = lambda a: int.from_bytes(rom[a:a+2], 'big')
l = lambda a: int.from_bytes(rom[a:a+4], 'big')
def area_ptr(tab, stage, area):
    t = l(tab + 4*stage)
    n = w(t)//2
    if area >= n: return None
    return t + w(t + 2*area)
def parse(p, maxn=400):
    out = []
    seen=set()   # (addr, kind-of-item, data)
    mode = w(p); p += 2
    out.append((p-2, 'mode', mode))
    steps = 0
    while steps < maxn:
        steps += 1
        if p in seen or p+16 > len(rom): break
        seen.add(p)
        d2 = w(p)
        if d2 & 0x8000:
            c = d2 & 0xfff
            if c == 0: out.append((p, 'cmd-mode', w(p+2))); p += 4
            elif c == 2: out.append((p, 'cmd-pause', 0)); p += 2
            elif c == 4: out.append((p, 'cmd-jump', l(p+2))); p = l(p+2)
            else: out.append((p, 'cmd?', d2)); break
            continue
        hdr = True
        first = True
        while True:
            if first:
                out.append((p, 'trigger', d2)); p += 2; first = False
            h = (w(p), w(p+2), w(p+4), w(p+6), l(p+8)); out.append((p, 'hdr', h)); p += 12
            while not (w(p) & 0x8000) and p+16 <= len(rom) and p not in seen:
                seen.add(p)
                e = rom[p:p+16]
                out.append((p, 'entry', dict(delay=w(p), cnt=w(p+2), x=w(p+4), y=w(p+6), tag=e[8], kind=e[9], p20=e[10], p21=e[11], b12=e[12], b13=e[13], b14=e[14], b15=e[15])))
                p += 16
            end = w(p) & 0xfff
            if p in seen and False: break
            out.append((p, 'end', end)); p += 2
            if end == 2: continue
            break
        if end == 4: break
    return out
if __name__ == '__main__':
    ft = int(sys.argv[1]) if len(sys.argv) > 1 else None
    fk = int(sys.argv[2]) if len(sys.argv) > 2 else None
    for tab in (0x5f5e, 0x5f7e):
        for stage in range(8):
            for area in range(12):
                ap = area_ptr(tab, stage, area)
                if ap is None: break
                items = parse(ap)
                if ft is None:
                    print('table %x stage %d area %d at %x: %d items' % (tab, stage, area, ap, len(items)))
                    continue
                for a, k, d in items:
                    if k == 'entry' and d['tag'] == ft and d['kind'] == fk:
                        print('table %x stage %d area %d entry @%x %s' % (tab, stage, area, a, d))
