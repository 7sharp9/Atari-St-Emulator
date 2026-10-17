"""summarize.py - table of the traj_track.py logs (agents/collide/tmp/run_<mode>_<seed>_g<gate>_<T>.log): frames matched per track and run."""
import re, os, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import sscfg
TMP = os.path.join(sscfg.WORK, 'agents', 'collide', 'tmp')
runs = [('random_3_g1', 'random joystick, 700 fr, R=0'), ('chase_5_g1', 'chase bot, 1500 fr, R=0'), ('chase_9_g1', 'chase bot, 2500 fr, R=0'),
        ('chase_6_g1', 'chase bot, 1500 fr, R=17, signs NOT ported'), ('chase_7_g1', 'chase bot, 1500 fr, R=8, signs NOT ported'), ('chase_26_g1', 'chase bot, 2500 fr, R=17 hazards, sign group ported'), ('chase_27_g1', 'chase bot, 1500 fr, R=8 hazards, sign group ported'), ('chase_5_g0', 'CONTROL chase 1500 without gate animator')]
print('%-44s' % 'run' + ''.join('  T%d        ' % (t + 1) for t in range(8)))
for key, label in runs:
    row = []
    for t in range(8):
        p = os.path.join(TMP, 'run_%s_%d.log' % (key, t))
        if not os.path.exists(p): row.append('-'); continue
        s = open(p).read(); m = re.search(r'frames (\d+), all fields\+map identical in (\d+)', s)
        if not m: row.append("running"); continue
        pl = re.search(r'plane0/1/2 mismatch frames: \[(\d+), (\d+), (\d+)\]', s); ga = re.search(r'gate array mismatches: (\d+)', s); cf = re.search(r'bad fields: (\{.*?\})', s)
        carbad = 0 if cf and cf[1] == '{}' else 1
        row.append('%s/%s%s' % (m[2], m[1], '*' if (carbad or (pl and pl[1] != '0') or (ga and ga[1] != '0')) else ''))
    print('%-44s' % label + ''.join('  %-10s' % x for x in row))
print('* = a car-field, gate-array or plane-0 mismatch exists; the plane-1/2 mismatches at R=8/17 are the flashing signs, see the report')
