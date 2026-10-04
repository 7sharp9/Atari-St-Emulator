#!/usr/bin/env python3
"""Differential gate: btai.c972 (ambient spawner) and btai.ca48 (boss fire) against callcap.
usage: gate_amb.py [N] [seed]"""
import random, sys
from btram import *
from btharness import Harness
import btai

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 3
h = Harness("play_start.snap")
base = h.base
rnd = random.Random(SEED)

def seed_for(want, tries=400):
    """find a RNG seed whose first draw (mod 1000) satisfies `want` (uses the reference rng)."""
    for _ in range(tries):
        s = rnd.randint(0, 65535)
        m = btai.Mem(base); m.sw_(btai.SEED, s)
        if want(btai.rng(m, 1000)):
            return s
    return rnd.randint(0, 65535)

def put(pk, a, v, n=2):
    for i in range(n):
        pk[a + i] = (v >> (8 * (n - 1 - i))) & 255

states = []
for i in range(N):
    kind = rnd.choice(["c972", "c972", "ca48"])
    pk = {}
    hx = rnd.randint(0x80, 0x700); hy = rnd.randint(0x40, 0x2c0)
    put(pk, 0x1F014, hx); put(pk, 0x1F016, hy)
    if kind == "c972":
        f40 = rnd.choice([0, 1, 1, 1]); f42 = rnd.choice([0, 1, 1, 1])
        put(pk, 0x17840, f40); put(pk, 0x17842, f42)
        put(pk, 0x1EEB8, 1 if rnd.random() < 0.1 else 0)
        pk[0x1F011] = rnd.choice([0, 1, 2, 5])
        # bias the seed: half the time make the first draw a "spawn" (<=7 or <=20)
        if rnd.random() < 0.7:
            s = seed_for(lambda r: r <= 20)
        else:
            s = rnd.randint(0, 65535)
        if rnd.random() < 0.05:                 # actor table full
            for k in range(0x1F030, 0x1F030 + 16 * 0xB3, 16):
                if base[k] == 0: pk[k] = 3
        tgt = "c972"; presets = {"A6": 0x1F020}
    else:
        put(pk, 0x1EEB8, 1 if rnd.random() < 0.8 else 0)
        pk[0x1F020] = rnd.choice([0, 0x11, 0x12, 0x13, 0x14])
        put(pk, 0x1F024, rnd.randint(0x80, 0x700)); put(pk, 0x1F026, rnd.randint(0x40, 0x2c0))
        if rnd.random() < 0.8:
            s = seed_for(lambda r: r <= 12)
        else:
            s = rnd.randint(0, 65535)
        if rnd.random() < 0.1:                  # shot table E full
            for k in range(30): pk[0x31612 + 14 * k] = 0
        tgt = "ca48"; presets = {}
    put(pk, btai.SEED, s)
    states.append(dict(name="amb_%04d_%s" % (i, kind), pokes=pk, presets=presets, target=tgt))

res, log = h.run(states)
ok = bad = 0; cnt = {}; types = {}
for stt in states:
    nm = stt["name"]; j = res.get(nm)
    if not j or j["outcome"] != "returned":
        print(nm, "no result"); bad += 1; continue
    ram = bytearray(base)
    for a, v in stt["pokes"].items(): ram[a] = v
    m = btai.Mem(ram)
    if stt["target"] == "c972":
        a6 = btai.c972(m, 0x1F020)
    else:
        btai.ca48(m); a6 = j["reg0"][14]
    want = m.diff()
    sp = j["entrySP"]
    got = {a: new for a, old, new in j["mem"] if not (sp - 256 <= a < sp + 8)}
    same = want == got and j["regN"][14] == a6
    newt = sorted({m.r[a] for a in want if 0x1F030 <= a < 0x1F030 + 16 * 0xB3 and (a - 0x1F030) % 16 == 0})
    for t_ in newt: types[t_] = types.get(t_, 0) + 1
    kind = stt["target"]
    spawned = any(0x1F030 <= a < 0x1F030 + 16 * 0xB3 or 0x31612 <= a < 0x317B6 for a in want)
    c = cnt.setdefault((kind, spawned), [0, 0]); c[1] += 1
    if same: ok += 1; c[0] += 1
    else:
        bad += 1
        print("FAIL", nm, sorted(set(want) ^ set(got))[:5], j["regN"][14], a6)
print("MATCH %d / %d" % (ok, ok + bad))
print({"%s%s" % (k, "+writes" if s else ""): "%d/%d" % tuple(v) for (k, s), v in sorted(cnt.items())})
print('actor types written by c972 (first byte):', types)
