#!/usr/bin/env python3
"""bottle_check.py <log>... : timeline of the fire-bottle thrower's bottle (pool 6 kind 4) and the fire it creates (pool a kind $10) from bottle_run.sh logs.
Prints: spawn of the thrower, the frame the bottle is released (64 and 66 clear), each state/mode of the bottle with its start frame, the frame of landing (bottle state 4), the fire's creation
frame and its modes with durations, the frame the bottle record is freed (life after landing), and every hp fall of player 1 with +63 and the attacker (+60) record."""
import sys, collections
def b(h, o): return int(h[2*o:2*o+2], 16)
def w(h, o): return int(h[2*o:2*o+4], 16)
for log in sys.argv[1:]:
    rel = None; bottle = {}; fire = {}; out = []; php = None; fireaddr = None; bottleaddr = None
    spawn = None; landing = None; fstart = None; bfree = None; ffree = None; thr = None
    prevb = None; fmodes = collections.OrderedDict(); bmodes = collections.OrderedDict(); hits = []; hold_end = None
    for line in open(log):
        p = line.split()
        if line.startswith('F '): rel = int(p[2].split('=')[1])
        elif line.startswith('SPAWN'): spawn = int(p[1].split('=')[1])
        elif line.startswith('R '):
            h = p[3]
            if p[1] == '6' and b(h, 19) == 4:
                bottleaddr = p[2]
                k = (b(h, 2), b(h, 3), b(h, 4), b(h, 64), b(h, 66))
                if k != prevb:
                    bmodes[(rel, k)] = 1; prevb = k
            if p[1] == 'a' and b(h, 19) == 0x10:
                fireaddr = p[2]
                if fstart is None: fstart = rel
                k = (b(h, 2), b(h, 3)); fmodes.setdefault(k, [rel, rel]); fmodes[k][1] = rel
            if p[1] == 'P':
                hp = w(h, 24)
                if php is not None and hp < php: hits.append((rel, php - hp, b(h, 63), w(h, 60)))
                php = hp
        elif line.startswith('X '):
            if p[2] == bottleaddr and bfree is None: bfree = rel
            if p[2] == fireaddr and ffree is None: ffree = rel
    print(log, 'thrower spawn rel', spawn)
    for (r, k) in bmodes: print('   bottle rel %d state.mode.step=%02x.%02x.%02x 64=%02x 66=%02x' % (r - 0, k[0], k[1], k[2], k[3], k[4]))
    print('   fire first frame', fstart, 'freed', ffree, 'modes', {('%02x.%02x' % k): (v[0] - fstart, v[1] - v[0] + 1) for k, v in fmodes.items()} if fstart else None)
    print('   bottle freed', bfree)
    for e in hits: print('   player hp fall rel %d (fire+%s): %d, r63=%02x attacker=%04x (fire record %s)' % (e[0], (e[0] - fstart) if fstart else '?', e[1], e[2], e[3], fireaddr))
