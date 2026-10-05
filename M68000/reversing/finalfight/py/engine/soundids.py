#!/usr/bin/env python3
"""Static census of the sound command ring (388(A5), queued by $9d0/$9de/$9e4/$9f8, drained one entry per two VBLs by $984 to the latch $800180).
Wrappers: $a10..$a42 (control commands, ungated) and $a48..$be6 (id wrappers that end in bra $9de or $9e4). Lists id -> callers (pc, kind of call, owner band).
usage: soundids.py [--json]"""
import os, sys, json
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(root, 'reversing', 'finalfight', 'py'))
from callers import callers
rom = open(os.path.join(root, 'scratchpad', 'finalfight', 'ff_main.bin'), 'rb').read()
w = lambda a: int.from_bytes(rom[a:a+2], 'big')
# wrappers
wr = {}   # addr -> (id, target)
a = 0xa10
while a < 0xbea:
    if w(a) == 0x303c:
        i = w(a+2); nxt = w(a+4)
        if (nxt & 0xff00) == 0x6000:
            d = nxt & 0xff
            tgt = a + 4 + 2 + (d if d < 0x80 else d - 256) if d != 0 else a + 4 + 2 + w(a+6)
            wr[a] = (i, tgt); a += 6 if d else 8; continue
    if w(a) == 0x4e75: a += 2; continue
    a += 2
BANDS = [(0x0000, 0x2800, 'kernel/system'), (0x2800, 0x4000, 'util/spawn'), (0x4000, 0x5000, 'phase/stage clock'), (0x5000, 0x6000, 'stage/phase 6 helpers'),
         (0x6000, 0x7000, 'placement/camera'), (0x7000, 0x7e00, 'hit resolution'), (0x7e00, 0x8000, 'player misc'), (0x8000, 0x10000, 'player (Cody/Guy/Haggar)'),
         (0x10000, 0x15000, 'attract/title seq'), (0x15000, 0x1a000, 'HUD/title'), (0x1a000, 0x21000, 'pool-8 kinds'), (0x21000, 0x2813a, 'kind 0 (Bred..)'),
         (0x2813a, 0x2a310, 'kind 1'), (0x2a310, 0x2ccac, 'kind 2'), (0x2ccac, 0x3136c, 'kind 3 (Andore)'), (0x3136c, 0x3514c, 'kind 4'), (0x3514c, 0x389b8, 'kind 5'),
         (0x389b8, 0x3c446, 'kind 6'), (0x3c446, 0x3d3d6, 'kinds 7,8'), (0x3d3d6, 0x40c6e, 'pool 4 DAMND'), (0x40c6e, 0x4b000, 'pool 4 other bosses'),
         (0x4b000, 0x51000, 'pool 4 / misc'), (0x51000, 0x56000, 'props (pool a)'), (0x56000, 0x5a000, 'debris/weapons'), (0x5a000, 0x5c000, 'pool 6/12 / HUD'),
         (0x5c000, 0x64000, 'scenes/test mode'), (0x64000, 0x80000, 'data')]
def band(pc):
    for lo, hi, n in BANDS:
        if lo <= pc < hi: return n
    return '?'
ids = {}
def add(i, pc, kind, via):
    ids.setdefault(i, []).append((pc, kind, via))
# direct callers with immediate in D0
def prev_imm(c):
    for back in range(2, 14, 2):
        x = c - back
        if w(x) == 0x303c: return w(x+2)
        if (w(x) & 0xf1ff) == 0x7000 and (w(x) >> 9) & 7 == 0: return w(x) & 0xff
    return None
for tgt, name in ((0x9d0, '$9d0'), (0x9de, '$9de'), (0x9e4, '$9e4'), (0x9f8, '$9f8')):
    for c, k in callers(tgt):
        if 0xa10 <= c < 0xbea: continue
        if 0x9d0 <= c < 0xa0e: continue
        i = prev_imm(c)
        add(i if i is not None else -1, c, k, name)
for wa, (i, tgt) in wr.items():
    for c, k in callers(wa):
        add(i, c, k, '$%x->$%x' % (wa, tgt))
if __name__ == '__main__':
    if '--json' in sys.argv:
        print(json.dumps({('%02x' % i if i >= 0 else '?'): v for i, v in ids.items()}))
    else:
        print('wrappers:', ' '.join('%x:%02x' % (a, i) for a, (i, t) in sorted(wr.items())))
        for i in sorted(ids):
            cs = ids[i]
            print('%s  %d callers: %s' % ('%02x' % i if i >= 0 else '?? (no immediate)', len(cs), ', '.join('%x(%s)' % (pc, band(pc)) for pc, k, v in sorted(cs))[:900]))
