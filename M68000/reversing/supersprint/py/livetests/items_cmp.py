"""items_cmp.py - compare data/items_<arm>.json (whole A4 window per frame) with items_ctl.json: per arm, frames where the whole window is
identical, and the set of A4-relative offsets (word-aligned) that ever differ, with the first frame."""
from lt import *
ctl = json.load(open(os.path.join(DATA, 'items_ctl.json')))
for arm in sys.argv[1:] or ['i0', 'i1', 'i2', 'i3']:
    a = json.load(open(os.path.join(DATA, 'items_%s.json' % arm)))
    W0 = a['W0']
    n = min(len(a['snaps']), len(ctl['snaps']))
    ident = 0; offs = {}
    for i in range(n):
        x, y = bytes.fromhex(a['snaps'][i]), bytes.fromhex(ctl['snaps'][i])
        if x == y: ident += 1; continue
        for j in range(0, len(x), 2):
            if x[j:j + 2] != y[j:j + 2]:
                o = W0 + j - A4
                offs.setdefault(o, i)
    print('arm %s vs ctl: %d/%d frames with the whole A4 window (9300 B) identical; %d distinct differing word offsets; first-diff frames: %s' % (
        arm, ident, n, len(offs), sorted(offs.items(), key=lambda kv: kv[1])[:12]))
    if arm == 'i3':
        print('   offsets that differ in i3:', sorted(offs))
