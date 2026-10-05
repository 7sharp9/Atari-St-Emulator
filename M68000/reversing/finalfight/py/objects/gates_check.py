#!/usr/bin/env python3
"""gates_check.py <out dir> : reads the logs written by gates.sh and prints one line per gate with "n of m" counts, then the failures. Exit status 1 if any gate fails.
Gates: fire schedule, player damage, box replay, fighter sampling model, fighter reach, bottle timeline, deflect, hovering deflect, pickup, shell, kind A/B (tile writes), kind 0
palette flicker, shadow kinds $1e/$1f (hide diff), kind $e door panels, bonus stage 6 objects, and the static kind map."""
import os, re, subprocess, sys, collections
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '../../../..'))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'scratchpad/finalfight/objects/out')
py = sys.executable
fails = []
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
def rw(a): return int.from_bytes(rom[a:a+2], 'big')
def b(h, o): return int(h[2*o:2*o+2], 16)
def w(h, o): return int(h[2*o:2*o+4], 16)
def L(name): return os.path.join(out, name + '.log')
def report(name, ok, n, note=''):
    print('%-34s %d of %d %s' % (name, ok, n, note))
    if ok != n: fails.append(name)
def records(log):
    """yield (rel, kind_char, addr, hex) for R lines and (rel, 'X', addr, None) for frees"""
    rel = None
    for l in open(log):
        p = l.split()
        if l.startswith('F '): rel = int(p[2].split('=')[1])
        elif l.startswith('R '): yield rel, p[1], p[2], p[3]
        elif l.startswith('X '): yield rel, 'X' + p[1], p[2], None
def fire_info(log):
    modes = collections.OrderedDict(); first = None; freed = None; addr = None; hits = []; php = None
    for rel, pool, a, h in records(log):
        if pool == 'a' and b(h, 19) == 0x10:
            addr = a
            if first is None: first = rel
            k = (b(h, 2), b(h, 3)); modes.setdefault(k, [rel, rel]); modes[k][1] = rel
        if pool == 'P':
            hp = w(h, 24)
            if php is not None and hp < php: hits.append((rel, php - hp, b(h, 63), w(h, 60), a))
            php = hp
        if pool == 'Xa' and a == addr and freed is None: freed = rel
    return first, freed, modes, hits, addr

# 1. fire schedule: 11/32/19/24 frames
logs = [f for f in sorted(os.listdir(out)) if re.match(r'(fd_|ff_|fp_|bt\d|bh_306)', f) and f.endswith('.log')]
ok = 0
for f in logs:
    first, freed, modes, hits, addr = fire_info(os.path.join(out, f))
    d = {k: v[1] - v[0] + 1 for k, v in modes.items()}
    good = first is not None and d.get((2, 0)) == 11 and d.get((2, 2)) == 32 and d.get((2, 4)) == 19 and d.get((2, 6)) == 24 and freed is not None
    ok += bool(good)
    if not good: print('   schedule mismatch', f, d)
report('fire schedule 11/32/19/24', ok, len(logs), '(logs: fd_, ff_, fp_, bt, bh_306)')

# 2. player damage 40, reaction 8, attacker = the fire record
ok = 0; fd = [f for f in sorted(os.listdir(out)) if f.startswith('fd_')]
for f in fd:
    first, freed, modes, hits, addr = fire_info(os.path.join(out, f))
    first_hit = [h for h in hits if h[4] == 'ff8568']
    good = len(first_hit) >= 1 and first_hit[0][1] == 40 and first_hit[0][2] == 8 and ('%06x' % (0xff0000 | first_hit[0][3])) == addr
    ok += bool(good)
report('player damage 40, r63 = 8, +60 = fire', ok, len(fd))

# 3. $7932 box replay: first predicted overlap = observed hp fall
ok = 0
for f in fd:
    o = subprocess.run([py, os.path.join(here, 'fire_overlap.py'), os.path.join(out, f)], capture_output=True, text=True).stdout
    m = re.search(r'frames \(fire\+n\): \[(\d+)[^\]]*\] observed hp falls \(fire\+n, delta\): \[\((\d+), (\d+)\)', o)
    ok += bool(m and m.group(1) == m.group(2) and m.group(3) == '40')
report('box replay = observed hit frame', ok, len(fd))

# 4. fighter sampling model over 8 start phases
o = subprocess.run([py, os.path.join(here, 'fire_phase.py')] + [os.path.join(out, 'fp_%d.log' % a) for a in range(200, 208)], capture_output=True, text=True).stdout
m = re.search(r'match (\d+) of (\d+)', o)
report('fighter $639e sampling model', int(m.group(1)) if m else 0, int(m.group(2)) if m else 8)
hit_phases = len(re.findall(r'observed fire\+\d+', o))
report('  fighter at +40: phases with a hit (of 8)', int(hit_phases == 4), 1, '(4 of 8 expected; counted %d)' % hit_phases)

# 5. fighter reach at the fixed phase of ff_*: hit for dx 0, 28, -41, -65; none for 40, 64, 80
exp = {0: True, 28: True, -41: True, -65: True, 40: False, 64: False, 80: False}
ok = 0
for dx, want in exp.items():
    o = subprocess.run([py, os.path.join(here, 'fire_fighter.py'), os.path.join(out, 'ff_%d.log' % dx)], capture_output=True, text=True).stdout
    got = 'fighter hit (fire+n, c167): None' not in o
    ok += (got == want)
report('fighter reach (central and -x boxes hit)', ok, len(exp))

# 6. natural bottle: landing, fire next frame, Cody hit 40 at fire+2
ok = 0; bt = ['bt1', 'bt2', 'bt4']
for t in bt:
    first, freed, modes, hits, addr = fire_info(L(t))
    st4 = None
    for rel, pool, a, h in records(L(t)):
        if pool == '6' and b(h, 19) == 4 and b(h, 2) == 4 and st4 is None: st4 = rel
    ph = [x for x in hits if x[4] == 'ff8568']
    ok += bool(first and st4 and first == st4 + 1 and ph and ph[0][0] - first == 2 and ph[0][1] == 40)
report('bottle: land, fire +1, hit +2 of 40', ok, len(bt))

# 7. punch in flight deflects: no fire, +2100 score; the late press (306) makes fire
ok = 0
for pr in (286, 290, 294, 298, 302):
    fire = None; sc0 = sc1 = None
    for rel, pool, a, h in records(L('bh_%d' % pr)):
        if pool == 'a' and b(h, 19) == 0x10 and fire is None: fire = rel
        if pool == 'P' and rel >= 199:
            s = int(h[264:272]); sc0 = sc0 if sc0 is not None else s; sc1 = s
    ok += (fire is None and sc1 - sc0 >= 2000)
report('deflect: no fire, +2000 or more', ok, 5)
fire = None
for rel, pool, a, h in records(L('bh_306')):
    if pool == 'a' and b(h, 19) == 0x10 and fire is None: fire = rel
report('late press: fire created', int(fire is not None), 1)

# 8. hovering bottle punched at rel 234: +2000 exactly
ok = 0
for t in ('df1', 'df2', 'df3', 'df4'):
    sc = []
    for rel, pool, a, h in records(L(t)):
        if pool == 'P' and rel >= 199: sc.append((rel, int(h[264:272])))
    jumps = [(sc[i][0], sc[i][1] - sc[i-1][1]) for i in range(1, len(sc)) if sc[i][1] != sc[i-1][1]]
    ok += (jumps == [(234, 2000)])
report('hover deflect +2000 at rel 234', ok, 4)

# 9. pickup: kinds 0 and 2 held (64 = ff, 66 = 2), kind 4 stays 74 = ff / 64 = 0, kind 3 flies off and is freed
def last_weapon(t, kind):
    r = None
    for rel, pool, a, h in records(L(t)):
        if pool == '6' and b(h, 18) == 6 and b(h, 19) == kind and rel >= 200: r = h
    return r
ok = 0
for k in (0, 2):
    h = last_weapon('pk%d' % k, k); ok += bool(h and b(h, 64) == 0xff and b(h, 66) == 2)
h = last_weapon('pk4', 4); ok += bool(h and b(h, 64) == 0 and b(h, 74) == 0xff)
h = last_weapon('pk3', 3); ok += bool(h and b(h, 2) == 6)
report('pickup: 0, 2 held; 4 not; 3 flies off', ok, 4)

# 10. shell hit: Cody 144 -> 104, reaction 3
php = None; ev = []
for rel, pool, a, h in records(L('sh2')):
    if pool == 'P':
        hp = w(h, 24)
        if php is not None and hp < php and rel >= 200: ev.append((php - hp, b(h, 63)))
        php = hp
report('shell: damage 40, r63 = 3', int(ev[:1] == [(40, 3)]), 1)

# 11. tile writes: A (record live) changes the map, B (records zeroed) does not
def gcount(log, region, lo, hi):
    rel = None; n = 0; wd = 0
    for l in open(log):
        p = l.split()
        if l.startswith('F '): rel = int(p[2].split('=')[1])
        elif l.startswith('G ') and p[1] == region and lo <= rel <= hi: n += 1; wd += int(p[3])
    return n, wd
ab = [('k6', 'scr2', 700, 1000), ('k7', 'scr3', 15, 90), ('k9', 'scr3', 600, 900), ('ka', 'scr2', 600, 900), ('k10', 'scr3', 400, 700), ('k3b', 'scr2', 496, 502)]
ok = 0
for t, reg, lo, hi in ab:
    a = gcount(L(t + '_A'), reg, lo, hi); bb = gcount(L(t + '_B'), reg, lo, hi)
    if t == 'ka': pass
    good = a[0] > bb[0] if t in ('k3b', 'ka') else (a[0] > 0 and bb[0] == 0)
    if t == 'k9': good = a[0] > 0 and bb[0] == 0
    print('   %-4s %s rel %d..%d: live %s, hidden %s' % (t, reg, lo, hi, a, bb))
    ok += bool(good)
report('kind tile writes (A live, B hidden)', ok, len(ab))

# 12. kind 0 palette flicker
pa = gcount(L('k0_ref'), 'pal', 102, 160); ph = gcount(L('k0_hid'), 'pal', 102, 160)
print('   palette frames with change rel 102..160: live %s, hidden %s' % (pa, ph))
report('kind 0 palette flicker', int(pa[0] > 40 and ph[0] == 0), 1)

# 13. shadows by hide diff
import numpy as np
from PIL import Image
snap = os.path.join(os.environ.get('FFA_RUN') or os.path.join(root, 'scratchpad/finalfight/objects/run'), 'snap')
def px(a, bn):
    A = np.array(Image.open(os.path.join(snap, a)).convert('RGB')).astype(int); B = np.array(Image.open(os.path.join(snap, bn)).convert('RGB')).astype(int)
    d = np.abs(A - B).sum(axis=2) > 0
    if not d.any(): return 0, None
    ys, xs = np.where(d); return int(d.sum()), (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()))
r1 = px('k1e_ref_0026.png', 'k1e_hid_0026.png'); r2 = px('k1f_ref_0706.png', 'k1f_hid_0706.png')
print('   $1e hide diff', r1, ' $1f hide diff', r2)
report('shadow kinds 1e and 1f (hide diff)', int(r1[0] > 0 and r1[1][3] - r1[1][2] <= 6) + int(r2[0] > 0 and r2[1][3] - r2[1][2] <= 6), 2)

# 14. kind $e with the flag and camera 2 poked: two records in window run modes 2, 4 and free; two stay in mode 6
st = collections.defaultdict(set); freed = set()
for rel, pool, a, h in records(L('e1')):
    if pool == '8' and b(h, 19) == 0x0e: st[a].add((b(h, 2), b(h, 3)))
    if pool == 'X8' and a in st: freed.add(a)
n4 = sum(1 for a, s in st.items() if (2, 4) in s); n6 = sum(1 for a, s in st.items() if (2, 6) in s and (2, 4) not in s)
report('kind e: 2 doors animate, 2 wait', int(n4 == 2 and n6 == 2 and len(freed) == 2), 1)

# 15. bonus stage 6 natural objects
kinds = collections.Counter()
seen = set()
for rel, pool, a, h in records(L('b6')):
    if pool == '8' and (a, b(h, 19), b(h, 20)) not in seen:
        seen.add((a, b(h, 19), b(h, 20))); kinds[b(h, 19)] += 1
report('bonus 6: kinds 12 x1, 2e x2, 31 x3', int(kinds[0x12] == 1 and kinds[0x2e] == 2 and kinds[0x31] == 3), 1)

# 16. static kind map: kind 7 has 10 placed entries in stage 2 area 1
o = subprocess.run([py, os.path.join(here, 'kindmap.py')], capture_output=True, text=True).stdout
blk = o.split('kind $07')[1].split('kind $08')[0]
report('kindmap: kind 7 entries in stage 2 area 1', int(len(re.findall(r'\[6[ef][0-9a-f]+ x=', blk)) == 10), 1)
d = subprocess.run([py, os.path.join(here, 'digest.py')], capture_output=True, text=True)
report('digest.py runs over 60 kinds', int(d.stdout.count('\nkind $') + d.stdout.startswith('kind $') == 60), 1)

print('FAILED: ' + ', '.join(fails) if fails else 'all gates pass')
sys.exit(1 if fails else 0)
