"""stats.py <probe.txt> [type hex]: per enemy type summary of a probe.lua log.
 - frames alive, state entries (count of times each state is entered) and frames spent in each state
 - attack instances: pool C box spawns grouped by (owner type, owner state, ctype); an instance = a run of consecutive frames
 - damage to P1 ($80113 writes): by (writer pc, ctype, owner type/state): count and total drop
 - score deltas of P1 (F line field 13) with the frame and the enemy states of the frame before
usage: stats.py out/<run>/probe.txt [type]"""
import sys, collections
path = sys.argv[1]
want = int(sys.argv[2], 16) if len(sys.argv) > 2 else None
A = collections.defaultdict(dict)   # frame -> slot -> bytes
F = {}
S = []
D = []
for line in open(path):
    p = line.split()
    if not p: continue
    if p[0] == "A": A[int(p[1])][int(p[2])] = bytes.fromhex(p[3])
    elif p[0] == "F": F[int(p[1])] = p
    elif p[0] == "S": S.append((int(p[1]), int(p[2]), int(p[3], 16), int(p[4], 16), int(p[5], 16), int(p[6], 16), int(p[7])))
    elif p[0] == "D":
        try: D.append((int(p[1]), int(p[2], 16), int(p[3], 16), int(p[4], 16), p[5], p[6], p[7], p[8], p[9], p[10], p[11]))
        except ValueError: pass
frames = sorted(F)
alive = collections.Counter()
entries = collections.defaultdict(collections.Counter)
inframes = collections.defaultdict(collections.Counter)
prev = {}
for f in frames:
    cur = {}
    for slot, b in A.get(f, {}).items():
        t = b[2]; st = b[3]
        cur[slot] = (t, b[16], st)
        alive[t] += 1
        inframes[t][st] += 1
        if prev.get(slot, (None, None, None))[2:] != (st,) or prev[slot][0] != t:
            entries[t][st] += 1
    prev = cur
for t in sorted(alive):
    if want is not None and t != want: continue
    print(f"== type {t:02x}: {alive[t]} enemy-frames")
    print("   state: entries / frames  " + "  ".join(f"{s:x}:{entries[t][s]}/{inframes[t][s]}" for s in sorted(inframes[t])))
inst = collections.Counter()
last = {}
for (f, slot, ot, ost, ov, ct, face) in S:
    if want is not None and ot != want: continue
    k = (ot, ost, ov, ct)
    if last.get((k, slot)) != f - 1: inst[k] += 1
    last[(k, slot)] = f
print("== attack box spawns (instance = run of consecutive frames): owner type, state, var, ctype -> instances")
for k, n in sorted(inst.items()): print(f"   type {k[0]:02x} state {k[1]:x} var {k[2]:x} ctype {k[3]:02x}: {n}")
dm = collections.defaultdict(lambda: [0, 0])
for d in D:
    f, old, new, pc, ct, cs, cf, os_, ot, ost, ov = d
    if old == 0 and f < 730: continue
    drop = old - new
    if drop <= 0: continue
    k = (pc, ct, ot, ost)
    dm[k][0] += 1; dm[k][1] += drop
print("== P1 health drops: writer pc, ctype, owner type, owner state -> count, total, per-event")
for k, (n, tot) in sorted(dm.items(), key=lambda kv: -kv[1][0]):
    if want is not None and k[2] != "%02x" % want and k[2] not in ("ffffffffffffffff",): continue
    print(f"   pc {k[0]:06x} ctype {k[1]} owner {k[2]} state {k[3]}: n={n} total={tot} each={tot/n:.2f}")
print("== P1 score steps (frame, delta, enemy states of previous frame)")
ps = None
for f in frames:
    if len(F[f]) < 14: continue
    sc = int(F[f][13], 16)
    if ps is not None and sc != ps:
        sl = {s: (b[2], b[3]) for s, b in A.get(f - 1, {}).items()}
        print(f"   frame {f}: {sc - ps:+x} (to {sc:x})  prev-frame enemies {[(hex(t), hex(s)) for t, s in sl.values()]}")
    ps = sc
