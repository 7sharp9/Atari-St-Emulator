#!/usr/bin/env python3
"""fire_overlap.py <log> [victim pool tag P|2] : per frame, test the overlap `$7932` would compute between the fire's attack box (+112 ptr, centre 116/118) and the victim's hurt box
(+120 ptr, centre 124/126; half sizes from the ROM at ptr+4/+6): x passes iff ((dx+s)&ffff) <= 2s with dx = 124(victim)-116(fire), s = hw(att)+hw(hurt); y likewise with
118/126 and the half heights. Prints the first predicted-overlap frames and the frame the victim's hp fell (from the log), so the two can be compared.
The record dump is taken at the end of a frame, after the updater and the hit resolution of that frame, so a predicted overlap at frame f has its effect in the same dump."""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
def rw(a): return int.from_bytes(rom[a:a+2], 'big')
def w(h, o): return int(h[2*o:2*o+4], 16)
def l(h, o): return int(h[2*o:2*o+8], 16)
log = sys.argv[1]; vp = sys.argv[2] if len(sys.argv) > 2 else 'P'
rel = None; fire = None; vic = None; first = None; lasthp = None; hits = []; pred = []
for line in open(log):
    p = line.split()
    if line.startswith('F '): rel = int(p[2].split('=')[1]); fire = None; vic = None
    elif line.startswith('R '):
        h = p[3]
        if p[1] == 'a' and int(h[38:40], 16) == 0x10: fire = h
        if p[1] == vp and (vp == 'P' or int(h[38:40], 16) == 0 and p[2] != 'ff9468'): vic = h
        if (fire is not None) and (vic is not None) and False: pass
    if fire is not None and vic is not None and p[0] == 'R':
        pass
    if fire is not None and vic is not None and (line.startswith('F ') is False):
        pass
    # evaluate once both are known for this frame, at the next F line
    if line.startswith('F ') and False: pass
    if fire is not None and vic is not None:
        if first is None: first = rel
        pa, ph = l(fire, 112) & 0xffffff, l(vic, 120) & 0xffffff
        if pa and ph:
            ax, ay, hx, hy = w(fire, 116), w(fire, 118), w(vic, 124), w(vic, 126)
            ahw, ahh, vhw, vhh = rw(pa + 4), rw(pa + 6), rw(ph + 4), rw(ph + 6)
            s = ahw + vhw; dx = (hx - ax) & 0xffff
            okx = ((dx + s) & 0xffff) <= 2 * s
            s2 = ahh + vhh; dy = (hy - ay) & 0xffff
            oky = ((dy + s2) & 0xffff) <= 2 * s2
            if okx and oky: pred.append(rel - first)
        hp = w(vic, 24)
        if lasthp is not None and hp < lasthp and hp != 0 and (lasthp - hp) < 0x100: hits.append((rel - first, lasthp - hp))
        lasthp = hp
        fire = None; vic = None
print(log, 'predicted overlap frames (fire+n):', pred[:12], 'observed hp falls (fire+n, delta):', hits[:4])
