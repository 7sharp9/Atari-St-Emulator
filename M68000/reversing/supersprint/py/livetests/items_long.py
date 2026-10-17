"""items_long.py <arm> - as items_ab.py but the whole race and the winner's circle: frame-aligned samples (every 100th frame) for NF frames,
then the entry of the winner's circle $1a4ca and 3 samples after it.  Output data/itemslong_<arm>.json (list of (tag, hex window))."""
from lt import *
arm = sys.argv[1]
NF = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
r = Repl2(os.path.join(AI, 'prerace_b.snap'))
if arm != 'ctl':
    setwords(r, {A4 - 4066 + 2 * int(arm[1]): 5})
r.cmd('kbd fe 80')
W0, WN = A4 - 9000, 9300
out_s = []
out, _ = r.cmd('bp df18 12000000'); assert any('hit' in l for l in out)
f = 0
while f < NF:                       # bounded: after the race the attract demo also calls $df18, so 'until it stops' never ends
    if f % 100 == 0:
        out_s.append(('f%d' % f, r.mem(W0, WN).hex()))
    out, _ = r.cmd('bp df18 600000')
    assert any('hit' in l for l in out)
    f += 1
out, _ = r.cmd('bp 1a4ca 20000000')
hit = any('hit' in l for l in out)
out_s.append(('wc_entry' if hit else 'wc_miss', r.mem(W0, WN).hex()))
for k in range(3):
    r.cmd('s 700000'); out_s.append(('wc+%d' % (k + 1), r.mem(W0, WN).hex()))
json.dump({'arm': arm, 'frames': f, 'wc': hit, 'snaps': out_s}, open(os.path.join(DATA, 'itemslong_%s.json' % arm), 'w'))
print(arm, 'race frames', f, 'winners circle reached', hit, 'samples', len(out_s), 'levels', r.a4w(-4066, 4))
r.close()
