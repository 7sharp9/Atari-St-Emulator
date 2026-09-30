"""probe.py - A/B key probes from a snapshot.
   probe(snap, actions, addrs, budget): actions = list of (kind, arg): ('kbd','3b') | ('s',n) | ('hits',n) | ('w',(addr,val)).
   Returns dict addr->count summed over all 'hits' segments, plus final regs and A4 flags."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *

HITRE = re.compile(r'^\s+\$([0-9a-f]+)\s+(\d+)\s+first\s+(-?\d+)\s+last\s+(-?\d+)')

def hits(r, n, addrs):
    out, regs = r.cmd('hits %d %s' % (n, ' '.join('%x' % a for a in addrs)))
    res = {}
    for l in out:
        m = HITRE.match(l)
        if m: res[int(m.group(1), 16)] = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
    return res, regs

def press(r, make, hold=60000, after=0):
    """make: list of hex scancode strings (make codes). Sends make, holds, sends break (make|0x80)."""
    r.cmd('kbd ' + ' '.join(make)); 
    r.cmd('s %d' % hold)
    r.cmd('kbd ' + ' '.join('%02x' % (int(m, 16) | 0x80) for m in make))
    if after: r.cmd('s %d' % after)

def flags(r, offs):
    return {o: r.g16(o) for o in offs}


class Acc:
    """accumulate hits over several segments"""
    def __init__(s, r, addrs):
        s.r, s.addrs, s.tot = r, addrs, {a: 0 for a in addrs}
        s.regs = None
    def run(s, n):
        h, regs = hits(s.r, n, s.addrs)
        for a, v in h.items(): s.tot[a] += v[0]
        s.regs = regs
        return h
    def kbd(s, *codes):
        s.r.cmd('kbd ' + ' '.join(codes))
    def press(s, make, hold=60000, after=0):
        s.kbd(*make); s.run(hold)
        s.kbd(*['%02x' % (int(m, 16) | 0x80) for m in make])
        if after: s.run(after)
    def show(s, tag=''):
        print(tag, {hex(k): v for k, v in s.tot.items() if v}, 'PC=%x' % s.regs['PC'])
