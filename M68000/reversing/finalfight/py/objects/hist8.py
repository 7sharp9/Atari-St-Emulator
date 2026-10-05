#!/usr/bin/env python3
"""hist8.py <log> [pool] [rel_from] : per record of a pool (default 8) in an sp.lua log: kind, +20, +21, record address, first/last rel frame, camera x at the first and the last frame, and the state histogram
as a list of (state.mode.step: frames). A record is identified by address and creation frame (a freed address reused later is a new record)."""
import sys, collections
log = sys.argv[1]; pool = sys.argv[2] if len(sys.argv) > 2 else '8'; frm = int(sys.argv[3]) if len(sys.argv) > 3 else 0
def b(h, o): return int(h[2*o:2*o+2], 16)
rel = None; cam = None; live = {}; done = []
def close(a, why):
    r = live.pop(a); r['last'] = rel; r['why'] = why; done.append(r)
frames = {}
for line in open(log):
    p = line.split()
    if line.startswith('F '):
        # account the frame that just ended (the keys are those after its R/X lines), then start the new frame
        for a, r in live.items():
            r['hist'][r['key']] += 1
        rel = int(p[2].split('=')[1]); cam = int(p[3].split('=')[1].split(',')[0], 16)
    elif line.startswith('R ') and p[1] == pool and rel is not None:
        h = p[3]; a = p[2]
        key = '%02x.%02x.%02x' % (b(h, 2), b(h, 3), b(h, 4))
        if a not in live:
            live[a] = dict(addr=a, kind=b(h, 19), b20=b(h, 20), b21=b(h, 21), first=rel, camfirst=cam, key=key, hist=collections.Counter(), x=int(h[12:16], 16), y=int(h[20:24], 16))
        live[a]['key'] = key
        # frame counting: the F line of this rel was already processed before the R lines, so add one for the frame of the change
    elif line.startswith('X ') and p[1] == pool and p[2] in live:
        close(p[2], 'freed')
for a, r in live.items(): r['hist'][r['key']] += 1
for a in list(live): close(a, 'live at end')
for r in sorted(done, key=lambda r: (r['kind'], r['first'])):
    if r['first'] < frm: continue
    print('kind %02x +20=%02x +21=%02x %s x=%04x y=%04x rel %d..%d (%s) cam %04x..: %s' % (r['kind'], r['b20'], r['b21'], r['addr'], r['x'], r['y'], r['first'], r['last'], r['why'], r['camfirst'], ' '.join('%s:%d' % (k, v) for k, v in r['hist'].items() if v)))
