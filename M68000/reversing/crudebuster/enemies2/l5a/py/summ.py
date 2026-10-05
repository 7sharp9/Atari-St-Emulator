"""Per-type summary of a drive5.lua log: state frame totals, state transition counts, hp changes, score events, death (last frames), pool B/C types seen.
usage: summ.py <log> <type hex> [slot-episode index]"""
import sys, collections
sys.path.insert(0, __import__('os').path.dirname(__file__))
from loglib import load, runs, u16
log, ty = sys.argv[1], int(sys.argv[2], 16)
F, eps = load(log)
sel = [e for e in eps if e.type == ty]
idx = int(sys.argv[3]) if len(sys.argv) > 3 else None
for k, ep in enumerate(sel):
    if idx is not None and k != idx: continue
    f0, f1 = ep.rows[0][0], ep.rows[-1][0]
    print(f"## episode {k}: slot {ep.slot} frames {f0}..{f1} ({len(ep.rows)} frames) var {ep.var}")
    fr = collections.Counter(b[3] for _, b in ep.rows)
    print("  frames per state:", " ".join(f"{s:x}:{n}" for s, n in sorted(fr.items())))
    rs = runs(ep)
    tr = collections.Counter((a[0], b[0]) for a, b in zip(rs, rs[1:]))
    print("  transitions:", " ".join(f"{a:x}>{b:x}:{n}" for (a, b), n in sorted(tr.items())))
    # runs per state: lengths
    ln = collections.defaultdict(list)
    for r in rs: ln[r[0]].append(r[3])
    print("  run lengths (state: n runs, min..max):", " ".join(f"{s:x}:{len(v)}x{min(v)}..{max(v)}" for s, v in sorted(ln.items())))
    hpe = [(f, b[5]) for f, b in ep.rows]
    ch = [(f, h) for (f, h), (f2, h2) in zip(hpe, hpe[1:]) if h2 != h]
    print("  start hp", ep.rows[0][1][5], "second row hp", ep.rows[1][1][5] if len(ep.rows) > 1 else None, "hp changes:", len(ch))
    # score events
    prev = None; ev = []
    for f in range(f0 - 1, f1 + 3):
        if f in F:
            sc = F[f].get('score')
            if prev is not None and sc != prev: ev.append((f, prev, sc))
            prev = sc
    st = {f: b[3] for f, b in ep.rows}
    print("  P1 score changes (frame, old, new, enemy state that frame/next):")
    for f, a, b in ev: print(f"    f{f}: {a:08x} -> {b:08x}  state {st.get(f, -1):x}/{st.get(f+1, -1):x}")
    print("  last 6 rows: " + " ".join(f"f{f}:s{b[3]:x}/hp{b[5]}/fl{b[0]:02x}" for f, b in ep.rows[-6:]))
