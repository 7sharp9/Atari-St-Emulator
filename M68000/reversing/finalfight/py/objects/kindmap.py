#!/usr/bin/env python3
"""kindmap.py : for every pool 8 kind $00-$3b, the placement entries (stage, area, init/trigger list, list address, x, y, +20, +21) of the live tables ($636e init, $6346 trigger)
and, from the static creator scan (reversing/finalfight/py/placement/sites.py logic), the code sites that allocate a pool 8 record with that kind constant.
Prints one block per kind. Imports the repo's placement readers by path; root from M68000_ROOT or __file__ (this directory must stay four levels below M68000/)."""
import os, sys, re, subprocess
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '../../../..'))
sys.path.insert(0, os.path.join(root, 'reversing/finalfight/py/placement'))
import placetab
A0 = placetab.areas(0x636e); A1 = placetab.areas(0x6346)
ent = {}
for s in range(6):
    for a, lst in enumerate(A0[s]):
        for e in placetab.initlist(lst):
            if e['sp'] == 8: ent.setdefault(e['kind'], []).append((s, a, 'init', e))
    for a, lst in enumerate(A1[s]):
        segs, end = placetab.trigmodes(lst)
        for mode, es in segs:
            for e in es:
                if e['sp'] == 8: ent.setdefault(e['kind'], []).append((s, a, 'trig', e))
# creators: reuse sites.py output (hex kind constants)
out = subprocess.run([sys.executable, os.path.join(root, 'reversing/finalfight/py/placement/sites.py')], capture_output=True, text=True).stdout
cre = {}
for line in out.splitlines():
    m = re.match(r'pool 8\s+site ([0-9a-f]+) in (.*?)\s+\(from ([0-9a-f]+)\) kind=\[(.*?)\] tagkind=\[.*?\] \+20=\[(.*?)\]', line)
    if not m: continue
    site, where, frm, ks, b20 = m.groups()
    for k in re.findall(r"'([0-9a-f]+)'", ks):
        cre.setdefault(int(k, 16), []).append('%s(%s)' % (site, where.split(' (')[0][:34]) + ('' if not b20 else ' +20=' + b20.replace("'", '')))
roots = [int.from_bytes(open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()[0x5872 + 4 * i:0x5872 + 4 * i + 4], 'big') for i in range(60)]
for k in range(0x3c):
    print('kind $%02x handler $%06x' % (k, roots[k]))
    byarea = {}
    for s, a, t, e in ent.get(k, []):
        byarea.setdefault((s, a, t), []).append(e)
    for (s, a, t), es in sorted(byarea.items()):
        print('   placed stage %d area %d %s: %s' % (s, a, t, ' '.join('[%s x=%04x y=%04x +20=%02x +21=%02x trig=%04x]' % (hex(e['addr'])[2:], e['x'], e['y'], e['c20'], e['c21'], e['trig']) for e in es)))
    if k in cre: print('   created by code at:', '; '.join(cre[k]))
    if k not in ent and k not in cre: print('   (no placement entry, no constant-kind allocator site)')
