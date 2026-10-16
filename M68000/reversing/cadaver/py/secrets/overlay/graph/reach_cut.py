"""reach_cut.py [--nodoors=7,8] [--spells] [goal ...] [--plan]: relax.py's closure from the CAD_LINEAGE_SNAP state (e.g. route_pocket.py's 25_drop89.snap), with geometry-blocked doors removed (--nodoors=7,8)."""
import sys, os
sys.path.insert(0, os.environ['M68000_ROOT'] + '/reversing/cadaver/py/secrets/overlay/graph')
import relax
nd = [int(x, 16) for a in sys.argv[1:] if a.startswith('--nodoors=') for x in a.split('=')[1].split(',') if x]
spells = '--spells' in sys.argv
sm, rx = relax.setup(spells=spells, no_doors=nd)
n = rx.run()
rooms = sorted(f[1] for f in rx.prov if f[0] == 'room'); items = sorted(f[1] for f in rx.prov if f[0] == 'item')
golds = sorted(f[1] for f in rx.prov if f[0] == 'gold')
print('start room', sm.w.lineage['room'], 'gold', sm.w.lineage['gold'], 'ruck', sm.w.lineage['ruck'])
print('rounds', n, 'rooms', len(rooms), rooms); print('items', items); print('gold values', golds)
for g in [a for a in sys.argv[1:] if not a.startswith('--')]:
    f = rx.reached(g); print(g, '->', 'layer %d' % rx.prov[f][1] if f else 'NOT REACHED')
    if f and '--plan' in sys.argv:
        for rnd, label, x in rx.plan(f): print('   %2d %-110s => %s' % (rnd, label[:150], x))
