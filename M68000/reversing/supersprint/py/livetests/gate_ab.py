"""gate_ab.py <T> <frame> <slot> [lead=12] [run=200] - same-snapshot A/B of the gate state at a drone's branch event.

gate_nat.py found drone `slot` crossing a gate-branch record at sample `frame` (frames counted from race_<T>.snap + 3M steps,
one per $df18 entry).  Replay to frame-`lead`, snapshot, then run `run` frames in three arms from that snapshot, sampling every
frame at $df18:
  nat    nothing poked
  flip   the gate is flipped to the opposite, coherent state: if it is open/opening (route 3) it is set to pos 1, dir -1, route 2
         (closing; the gate re-blits its mask each animation frame); if closed (route 2) to pos 3, dir +1, route 3 (opening).
  hold   the same state as nat, but with the gate timer pushed to 0x7000 where the gate is idle (null variable: arm proves the
         poke path alone changes nothing; only run when the gate is idle at the snapshot)
Reports the drone's wp path, branch taken, and every frame whose flag (-3778) or stun (-3810) is nonzero for any drone.
Output data/gate_ab_<T>_<frame>_<slot>.json."""
from lt import *
from wptables import table, COUNT
T, FR, SLOT = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
LEAD = int(sys.argv[4]) if len(sys.argv) > 4 else 12
RUN = int(sys.argv[5]) if len(sys.argv) > 5 else 200
SN = os.path.join(sscfg.WORK, 'agents', 'tracks', 'snaps')
snap = os.path.join(DATA, 'gate_%d_%d_L%d.snap' % (T, FR, LEAD))
if not os.path.exists(snap):
    r = Repl2(os.path.join(SN, 'race_%d.snap' % T))
    r.cmd('s 3000000')
    for _ in range(FR - LEAD):
        out, _ = r.cmd('bp df18 400000'); assert any('hit' in l for l in out)
    r.cmd('snap %s' % snap); r.close()
tb = table(T); cnt = COUNT[T]
res = {}
for arm in ('nat', 'flip', 'hold'):
    r = Repl2(snap)
    s0 = sample(r)
    ng = r.a4w(-1808, 1)[0]
    # the gate the drone is heading for
    nxt = (s0['wp'][SLOT] + 2) % cnt
    g = None
    for k in range(0, 8, 2):
        n = (s0['wp'][SLOT] + 2 + k) % cnt
        if tb[n][3] & 0x200: g = tb[n][3] & 3; break
    gp = r.a4w(-1820, 3); gd = r.a4w(-1814, 3); gr = r.a4w(-1832, 3); gt = r.a4w(-1826, 3)
    pk = {}
    if arm == 'flip':
        if gr[g] == 3: pk = {A4 - 1820 + 2 * g: 1, A4 - 1814 + 2 * g: -1, A4 - 1832 + 2 * g: 2}
        else: pk = {A4 - 1820 + 2 * g: 3, A4 - 1814 + 2 * g: 1, A4 - 1832 + 2 * g: 3}
    elif arm == 'hold':
        if gd[g] != 0:
            r.close(); continue          # gate is animating at the snapshot: the hold arm needs an idle gate
        pk = {A4 - 1826 + 2 * g: 0x7000}
    if pk: setwords(r, pk)
    rows = []
    for f in range(RUN):
        out, _ = r.cmd('bp df18 400000'); assert any('hit' in l for l in out)
        s = sample(r)
        s['gpos'] = r.a4w(-1820, 3); s['gdir'] = r.a4w(-1814, 3); s['grt'] = r.a4w(-1832, 3)
        rows.append(s)
    res[arm] = {'rows': rows, 'gate': g, 'start': {'pos': gp, 'dir': gd, 'route': gr, 'timer': gt}, 'poke': {hex(k): v for k, v in pk.items()}}
    r.close()
json.dump(res, open(os.path.join(DATA, 'gate_ab_%d_%d_%d.json' % (T, FR, SLOT)), 'w'))
for arm, d in res.items():
    rows = d['rows']
    path = []
    for x in rows:
        w = x['wp'][SLOT]
        if not path or path[-1] != w: path.append(w)
    bad = [(i, [(s, x['flag'][s], x['stun'][s]) for s in range(4) if x['flag'][s] or x['stun'][s]]) for i, x in enumerate(rows) if any(x['flag'][s] or x['stun'][s] for s in range(4))]
    print('T%d f%d slot %d arm %-4s gate %s start %s poke %s' % (T, FR, SLOT, arm, d['gate'], d['start'], d['poke']))
    print('    wp path of slot %d: %s' % (SLOT, path[:12]))
    print('    gate end pos %s route %s; frames with flag/stun on any car: %d %s' % (rows[-1]['gpos'], rows[-1]['grt'], len(bad), bad[:3]))
