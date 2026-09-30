"""f5_frames.py - which (animation, image) pairs does the winner's circle draw via $1b4e4(screen, anim, image), with and
without F5 held at the poll?  First 40 calls after the poll, from snap/pre_winner.snap."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
SNAP = os.path.join(AGENT, 'snap', 'pre_winner.snap')
for tag, key in (('no key', None), ('F5 held', ['3f'])):
    r = R(SNAP)
    if key: r.cmd('kbd ' + ' '.join(key)); r.cmd('s 60000')
    r.cmd('u 1ad44 30000000')
    seq = []; tick = []
    for i in range(45):
        out, g = r.cmd('u 1b4e4 30000000')
        if g['PC'] != 0x1b4e4: break
        sp = g['A7']
        anim = r.w16(sp + 8); img = r.w16(sp + 10)
        seq.append((anim, img))
        r.cmd('s 1')
    # collapse consecutive repeats
    comp = []
    for x in seq:
        if not comp or comp[-1][0] != x: comp.append([x, 1])
        else: comp[-1][1] += 1
    print(tag, 'calls', len(seq), 'distinct (anim,img) runs:', [(a, i, n) for (a, i), n in comp][:24])
    r.close()
