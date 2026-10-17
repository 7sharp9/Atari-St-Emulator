"""items_long_cmp.py [arm...] - compare data/itemslong_<arm>.json with itemslong_ctl.json sample by sample (event-aligned: every 100th $df18 entry,
then the winner's-circle entry and three 700k-step samples after it)."""
from lt import *
c = json.load(open(os.path.join(DATA, 'itemslong_ctl.json')))
for arm in sys.argv[1:] or ['i3', 'i1']:
    a = json.load(open(os.path.join(DATA, 'itemslong_%s.json' % arm)))
    n = min(len(a['snaps']), len(c['snaps']))
    ident = 0; offs = {}
    for i in range(n):
        (tg, x), (tc, y) = a['snaps'][i], c['snaps'][i]
        assert tg == tc
        x, y = bytes.fromhex(x), bytes.fromhex(y)
        if x == y: ident += 1; continue
        for j in range(0, len(x), 2):
            if x[j:j + 2] != y[j:j + 2]: offs.setdefault(-9000 + j, tg)
    print('arm %s vs ctl: %d/%d event-aligned samples with the whole A4 window identical; %d differing word offsets: %s' % (arm, ident, n, len(offs), sorted(offs.items())[:8]))
