"""Check the AI chooser ($2438a) prediction against a live log. For each transition of a pool A episode of <type> out of a state that calls the chooser
(default 6 and 7; pass others) the expected set of next states is computed from the enemy position (+8,+12), the player position and state (F line: px, py, p1st, p1sub)
exactly as $2438a does (T1/T2/T3 and dx>>4 bucket; sub-table index = P1 state&f then P1 sub-state), using the leaf decoder of chooser.py. 'ok' = the new state is in the set.
usage: chooser_check.py <log> <type hex> [source states hex csv]
Positions come from the log row of the frame the state changed (the frame whose handler ran the chooser; players are updated before the pool dispatch, so F of the same frame is what $22bd0 copied)."""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from loglib import load, u16
import chooser as C
log, ty = sys.argv[1], int(sys.argv[2], 16)
src = [int(x, 16) for x in (sys.argv[3] if len(sys.argv) > 3 else "6,7").split(",")]
F, eps = load(log)
def leaf_states(addr):
    out = set()
    for s in C.walk(addr):
        if s.startswith("state "): out.add(int(s.split()[1], 16))
        elif s.startswith("rand4["):
            for part in s[6:-1].replace(" | ", "|").split("|"):
                for q in part.split(","):
                    if q.startswith("state "): out.add(int(q.split()[1], 16))
        # jumpparams: no state
    return out
def predict(ex, ey, tx, tyy, tst, tsub):
    """returns (table, bucket, leaf address or None, expected states)"""
    D = lambda a, b: (a - b) & 0xffff
    if ((tyy + 0x60) & 0xffff) < ey: name, thr = "T2", 0x30
    elif ((tyy - 0x20) & 0xffff) < ey: name, thr = "T1", 0x10
    else: name, thr = "T3", 0x30
    dx = (tx - ex) if tx >= ex else (ex - tx)
    if dx >= 0x100: return name, 0x10, None, {7}
    b = dx >> 4
    base = C.T[name]; p1 = C.l(base + 4 * ty); p2 = C.l(p1 + 4 * b)
    if name == "T1":
        p3 = C.l(p2 + 4 * (tst & 0xf)); leaf = C.l(p3 + 4 * tsub)
    else: leaf = p2
    return name, b, leaf, leaf_states(leaf) if 0x400 <= leaf < 0x2c000 else None
res = collections.Counter(); bad = []
leafcount = collections.Counter()
for ep in eps:
    if ep.type != ty: continue
    for (f0, b0), (f1, b1) in zip(ep.rows, ep.rows[1:]):
        if b0[3] in src and b1[3] != b0[3] and f1 == f0 + 1 and b1[3] not in (1, 2, 3, 4, 5):
            if f1 not in F: continue
            Fr = F[f1]
            ex, ey = u16(b1, 8), u16(b1, 12)
            # +42/+44 were copied by $22bd0 in the chooser: use them (exact) when present
            tx, tyy = u16(b1, 42), u16(b1, 44)
            tst, tsub = b1[46], b1[47]
            name, bk, leaf, exp = predict(u16(b1, 8), u16(b1, 12), tx, tyy, tst, tsub)
            key = (name, bk, f"{leaf:06x}" if leaf else "walk")
            leafcount[key] += 1
            if exp is None: res["unknown"] += 1
            elif b1[3] in exp: res["ok"] += 1
            elif b0[3] in (7, 8, 9) and b1[3] == 6: res["natural end of a walk/hop/jump (not a chooser call)"] += 1
            elif ty in (0x4d, 0x10) and b0[3] == 6 and b1[3] == 8 and b0[30] == 0x7f: res["4d idle timeout (byte +30 reached $80 in state 6, $15e76)"] += 1
            elif b1[3] == 0x11 and ty in (0x4b, 0x0d): res["external: owner state 11 set by the skull head ($1f2e4)"] += 1
            else:
                res["MISS"] += 1; bad.append((f1, b0[3], b1[3], key, sorted(exp)))
print("result", dict(res))
for x in bad[:15]: print("  miss", x)
print("leaf use (table, dx bucket, leaf):", dict(sorted(leafcount.items())))
