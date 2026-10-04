#!/usr/bin/env python3
"""Differential gate: btai.e7e2 (animation-event attacks of types 9, 10, $c, $11, $12, $13) against
`callcap e7e2 A3=...`.  usage: gate_events.py [N] [seed]   (default 600, 4)"""
import random, sys
from btram import *
from btharness import Harness
import btai

N = int(sys.argv[1]) if len(sys.argv) > 1 else 600
rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
h = Harness("play_start.snap"); base = h.base
A3 = 0x1F290
def put(pk, a, v): pk[a], pk[a + 1] = (v >> 8) & 255, v & 255
states = []; meta = {}
for i in range(N):
    t = rnd.choice([9, 10, 0xC, 0x11, 0x12, 0x13, 0x11, 0x12, 5, 3])
    pk = {A3: t, A3 + 1: rnd.choice([0, 1, 3, 4, 8]), A3 + 3: rnd.randint(0, 1), A3 + 9: rnd.choice([0, 0, 5])}
    hx = rnd.randint(0x80, 0x700); hy = rnd.randint(0x40, 0x2c0)
    put(pk, A3 + 4, (hx + rnd.randint(-300, 300)) & 0xFFFF); put(pk, A3 + 6, hy + rnd.randint(-100, 100))
    put(pk, 0x1F014, hx); put(pk, 0x1F016, hy)
    put(pk, btai.SEED, rnd.randint(0, 65535))
    if rnd.random() < 0.12:                        # P table nearly full / full
        for k in range(rnd.randint(27, 30)): put(pk, btai.PTAB + 14 * k, 0)
    states.append(dict(name="ev_%04d_t%d" % (i, t), pokes=pk, presets={"A3": A3}, target="e7e2"))
    meta[states[-1]["name"]] = t
res, log = h.run(states)
ok = 0; by = {}; spawned = {}
for st in states:
    j = res.get(st["name"])
    if not j or j["outcome"] != "returned": print(st["name"], "no result"); continue
    ram = bytearray(base)
    for a, v in st["pokes"].items(): ram[a] = v
    m = btai.Mem(ram); btai.e7e2(m, A3)
    want = m.diff(); sp = j["entrySP"]
    got = {a: n for a, o, n in j["mem"] if not (sp - 256 <= a < sp + 8)}
    t = meta[st["name"]]; c = by.setdefault(t, [0, 0]); c[1] += 1
    nsh = sum(1 for k in range(30) if m.w(btai.PTAB + 14 * k) != base[btai.PTAB + 14 * k] * 256 + base[btai.PTAB + 14 * k + 1])
    spawned[t] = spawned.get(t, 0) + nsh
    if want == got and j["regN"][11] == A3: ok += 1; c[0] += 1
    else: print("FAIL", st["name"], sorted(set(want) ^ set(got))[:5])
print("MATCH %d / %d" % (ok, len(states)))
print("by type:", {hex(t): "%d/%d" % tuple(c) for t, c in sorted(by.items())})
