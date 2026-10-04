#!/usr/bin/env python3
"""Urn / container drop roll ($d4ae path $d5d0..$d648).  A cracked urn (map object kind 2) overlapping
a hero shot is hit by `callcap d4ae`; the game rolls rng(level*4+16) into the table $17784.  Prediction
from the code read: byte b = $17784[roll]; b < $80: the record becomes pickup kind b (same x,y);
b >= $80: villains of actor type (b & $7f) are spawned at the urn (3 of them for type $f, else 1) and the
record is cleared.  The roll is computed with the gated reference rng.  usage: gate_urn.py [seeds_per_level]"""
import random, sys
from btram import *
from btharness import Harness
import btai

K = int(sys.argv[1]) if len(sys.argv) > 1 else 12
h = Harness("play_start.snap"); base = h.base
rnd = random.Random(5)
def put(pk, a, v):
    pk[a], pk[a + 1] = (v >> 8) & 255, v & 255
states = []
for lvl in range(8):
    for k in range(K):
        pk = {}
        sx, sy = 0x100, 0x100
        put(pk, 0x1EFEC, sx); put(pk, 0x1EFEE, sy)
        put(pk, 0x17846, lvl)
        ux, uy = sx + 0x60, sy + 0x60
        put(pk, 0x1FB60, 2); put(pk, 0x1FB62, ux); put(pk, 0x1FB64, uy); pk[0x1FB66] = 0; pk[0x1FB67] = 0
        put(pk, 0x31592, 0); put(pk, 0x31594, ux); put(pk, 0x31596, uy)     # hero shot H0 exactly on the urn
        put(pk, 0x31592 + 12, 0)
        sd = rnd.randint(0, 65535); put(pk, btai.SEED, sd)
        states.append(dict(name="urn_l%d_%02d" % (lvl, k), pokes=pk, presets={}, target="d4ae", steps=3000000, _p=(lvl, sd, ux, uy)))
res, log = h.run(states)
ok = tot = 0; kinds = {}
for st in states:
    j = res.get(st["name"])
    if not j or j["outcome"] != "returned": print(st["name"], "no result"); continue
    lvl, sd, ux, uy = st["_p"]
    m = btai.Mem(base); m.sw_(btai.SEED, sd)
    roll = btai.rng(m, lvl * 4 + 16)
    b = base[0x17784 + roll]
    mem = {a: n for a, o, n in j["mem"]}
    rec = (mem.get(0x1FB60, 0) << 8) | mem.get(0x1FB61, base[0x1FB61])
    new_actor_types = sorted(mem[a] for a in mem if 0x1F030 <= a < 0x1F030 + 16 * 179 and (a - 0x1F030) % 16 == 0 and mem[a])
    if b < 0x80:
        good = rec == b and not new_actor_types
        key = "item%d" % b
    else:
        want = [b & 0x7F] * (3 if (b & 0x7F) == 0xF else 1)
        good = new_actor_types == sorted(want) and rec == 0
        key = "villain%d" % (b & 0x7F)
    tot += 1; ok += good
    kinds[key] = kinds.get(key, 0) + 1
    if not good: print("MISMATCH", st["name"], "roll", roll, "b", b, "rec", rec, "actors", new_actor_types)
print("urn drop prediction MATCH %d / %d" % (ok, tot)); print(kinds)
