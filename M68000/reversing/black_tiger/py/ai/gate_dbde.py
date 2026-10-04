#!/usr/bin/env python3
"""Differential gate: btai.dbde ($dbde actor AI step) against `callcap dbde` over a synthetic corpus.

usage: gate_dbde.py [N] [seed] [snap]      (defaults 600, 1, play_start.snap)
Pokes are labelled in the state names; the poked fields are +0 type, +1 state, +3 facing, +4/+6
position, +9/+12/+13 timers, hero x/y ($1f014/$1f016) and the RNG seed ($3195c).
"""
import random, struct, sys
from btram import *
from btharness import Harness
import btai

N = int(sys.argv[1]) if len(sys.argv) > 1 else 600
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 1
SNAP = sys.argv[3] if len(sys.argv) > 3 else "play_start.snap"

h = Harness(SNAP)
base = h.base
rnd = random.Random(SEED)
A3 = 0x1F290                                    # an unused record (index 17 after the hero)
assert base[A3] == 0 and base[A3 + 16] == 0
P = l(base, 0x1EEA2)
width_px = w(base, 0x1EFFE)

def reach(t):
    a0 = (P + l(base, P + (t - 1) * 4)) & 0xFFFFFFFF
    return sw(base, a0 + 10), sw(base, a0 + 12)

states = []
meta = {}
for i in range(N):
    t = rnd.randint(1, 19) if rnd.random() < 0.8 else rnd.choice([6, 15, 17, 17])   # bias to the fire / state-8 / 20% branches
    r, e = reach(t)
    hx = rnd.randint(0x80, width_px - 0x80)
    hy = rnd.randint(0x40, 0x2c0)
    mode = rnd.random()
    if mode < 0.55:                             # close to the hero, around the reach thresholds
        dx = rnd.choice([r - e, r + e, r, r - 2 * e, e, 0, 0x30, 0x40, 0x41, 0x28 - e + e, r - 1, r + 1]) + rnd.randint(-3, 3)
        dx *= rnd.choice([-1, 1])
        ax = (hx + dx) % width_px
        ay = hy + rnd.choice([0, -0x10, 0x10, 0x30, -0x40, 0x41, -0x41])
    else:
        ax = rnd.randint(0, width_px - 1)
        ay = rnd.randint(0x20, 0x2d0)
    st = rnd.choice([0, 0, 0, 6, 6, 6, 1, 2, 5, 7]) if rnd.random() < 0.95 else rnd.randint(0, 9)
    pk = {A3: t, A3 + 1: st, A3 + 2: rnd.randint(0, 5), A3 + 3: rnd.randint(0, 1)}
    pk[A3 + 4], pk[A3 + 5] = (ax >> 8) & 255, ax & 255
    ay &= 0xFFFF
    pk[A3 + 6], pk[A3 + 7] = (ay >> 8) & 255, ay & 255
    pk[A3 + 8] = 3
    pk[A3 + 9] = 0 if rnd.random() < 0.9 else rnd.randint(1, 5)
    if rnd.random() < 0.1:
        pk[A3 + 12] = rnd.randint(1, 8); pk[A3 + 13] = rnd.randint(0, 9)
    pk[0x1F014], pk[0x1F015] = (hx >> 8) & 255, hx & 255
    pk[0x1F016], pk[0x1F017] = (hy >> 8) & 255, hy & 255
    sd = rnd.randint(0, 65535)
    pk[SEED_ADDR := 0x3195C], pk[0x3195D] = sd >> 8, sd & 255
    # sibling record (writes at +17/+19 for types 12/13/18): make it a defined plain record
    name = "dbde_%04d_t%d_s%d" % (i, t, st)
    states.append(dict(name=name, pokes=pk, presets={"A3": A3}, target="dbde"))
    meta[name] = (t, st)

res, log = h.run(states, "dbde")
print("states", len(states), "outputs", len(res))
ok = bad = 0
by_type = {}
fails = []
for stt in states:
    nm = stt["name"]
    if nm not in res:
        print("MISSING", nm); bad += 1; continue
    j = res[nm]
    if j["outcome"] != "returned":
        print(nm, "outcome", j["outcome"]); bad += 1; continue
    ram = bytearray(base)
    for a, v in stt["pokes"].items():
        ram[a] = v
    m = btai.Mem(ram)
    ret = btai.dbde(m, A3)
    want = {a: v for a, v in m.diff().items()}
    sp = j["entrySP"]                          # callcap's own pushes live just below entrySP
    got = {a: new for a, old, new in j["mem"] if not (sp - 256 <= a < sp + 8)}
    # callcap lists only bytes whose value changed relative to the poked RAM
    d0 = j["regN"][0]
    d0_ref = ret if ret is not None else j["reg0"][0]
    same = (want == got) and (d0 == d0_ref) and j["regN"][11] == A3
    t, s_ = meta[nm]
    c = by_type.setdefault(t, [0, 0])
    c[1] += 1
    if same:
        ok += 1; c[0] += 1
    else:
        bad += 1
        if len(fails) < 8:
            fails.append((nm, sorted(set(want) ^ set(got))[:6], {a: (want.get(a), got.get(a)) for a in sorted(set(want) ^ set(got))[:4]}, hex(d0), hex(d0_ref)))
print("MATCH %d / %d" % (ok, ok + bad))
print("by type:", " ".join("%d:%d/%d" % (t, c[0], c[1]) for t, c in sorted(by_type.items())))
for f in fails: print("FAIL", f)
print("branch coverage:", dict(sorted(btai.COV.items())))
