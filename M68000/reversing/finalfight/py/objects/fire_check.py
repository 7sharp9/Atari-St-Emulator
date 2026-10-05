#!/usr/bin/env python3
"""fire_check.py <log>... : from fire_run.sh logs, the fire's schedule and every hp change of the player and the fighter.
Prints the fire record's frames per (state, mode) with its attack-box frames, the attack box indices seen, then each hp change (frame, victim, delta, +63, +60 attacker) and
the frame offset from the fire's first frame."""
import sys, collections
def b(h, o): return int(h[2*o:2*o+2], 16)
def w(h, o): return int(h[2*o:2*o+4], 16)
for log in sys.argv[1:]:
    rel = None; fire = None; first = None; modes = collections.OrderedDict(); atk = collections.Counter(); last = {}; ev = []; freed = None
    atkframes = collections.defaultdict(list)
    fireaddr = None
    for l in open(log):
        p = l.split()
        if l.startswith('F '): rel = int(p[2].split('=')[1])
        elif l.startswith('R '):
            h = p[3]
            if p[1] == 'a' and b(h, 19) == 0x10:
                fireaddr = p[2]
                if first is None: first = rel
                k = (b(h, 2), b(h, 3)); modes.setdefault(k, [rel, rel]); modes[k][1] = rel
                atkframes[b(h, 45)].append(rel)
                atk[b(h, 45)] += 1
            if p[1] in ('P', '2'):
                key = (p[1], p[2])
                hp = w(h, 24); old = last.get(key)
                if old is not None and hp != old:
                    ev.append((rel, p[1], hp - old if hp >= old else -(old - hp), b(h, 63), w(h, 60)))
                last[key] = hp
        elif l.startswith('X ') and p[2] == fireaddr and freed is None: freed = rel
    print(log, 'fire first frame', first, 'freed', freed, 'life', (freed - first) if freed else None)
    cum = 0
    for k, (a, z) in modes.items():
        print('  state/mode %02x.%02x frames %d..%d (dur %d)' % (k[0], k[1], a, z, z - a + 1))
    print('  attack box idx seen (frames with idx): ', dict(sorted(atk.items())))
    for idx in sorted(atkframes): 
        if idx: print('   idx %d at rel+%s' % (idx, ','.join(str(f - first) for f in atkframes[idx][:8])), '...' if len(atkframes[idx]) > 8 else '')
    for e in ev: print('  hp change rel %d (fire+%d) pool %s delta %d r63=%02x attacker=%04x' % (e[0], e[0] - first, e[1], e[2], e[3], e[4]))
