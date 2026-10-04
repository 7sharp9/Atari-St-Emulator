#!/usr/bin/env python3
"""Activation window of the actor loop $e19e: an actor is updated (AI $dbde runs, which writes the
word $1eeae) iff  0 <= (x - scrollx [+ wrap if negative]) + $40 <= $1a0  and  0 <= y - scrolly <= $c8
(signed word compares, $e1e6..$e220).  Probe: every other actor cleared, one type-3 actor in state 0
placed around the window edges, `callcap e19e`; predicted vs observed $1eeae write.
usage: gate_window.py [seed]"""
import random, sys
from btram import *
from btharness import Harness

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 2
rnd = random.Random(seed)
h = Harness("play_start.snap")
base = h.base
A3 = 0x1F290
wrap = w(base, 0x1EFFE)

def put(pk, a, v): pk[a], pk[a + 1] = (v >> 8) & 255, v & 255

def predict(ax, ay, sx, sy):
    d3 = ((ax - sx + 0x8000) & 0xFFFF) - 0x8000
    if d3 < 0: d3 += wrap
    d3 = ((d3 + 0x40 + 0x8000) & 0xFFFF) - 0x8000
    if d3 < 0 or d3 > 0x1A0: return False
    d3 = ((ay - sy + 0x8000) & 0xFFFF) - 0x8000
    return 0 <= d3 <= 0xC8

states = []
for i in range(160):
    pk = {}
    for k in range(0x1F020, 0x1F020 + 16 * 179, 16):
        if base[k]: pk[k] = 0
    sx = rnd.choice([0, 8, 0x100, 0x200, wrap - 0x100, wrap - 0x10]); sy = rnd.choice([0x100, 0x258, 0x20])
    edge = rnd.choice([-0x41, -0x40, -0x3f, 0x160, 0x15f, 0x161, rnd.randint(-0x80, 0x180), rnd.randint(-0x80, 0x180)])
    ax = (sx + edge) % wrap
    ay = sy + rnd.choice([-1, 0, 1, 0xC7, 0xC8, 0xC9, rnd.randint(-20, 230)])
    pk[A3] = 3; pk[A3 + 1] = 0; pk[A3 + 2] = 0; pk[A3 + 3] = 0; pk[A3 + 8] = 3; pk[A3 + 9] = 0
    put(pk, A3 + 4, ax); put(pk, A3 + 6, ay & 0xFFFF)
    put(pk, 0x1EFEC, sx); put(pk, 0x1EFEE, sy); put(pk, 0x1EEAE, 0xFFFF)
    states.append(dict(name="win_%03d" % i, pokes=pk, presets={}, target="e19e", steps=4000000, _p=(ax, ay, sx, sy)))
res, log = h.run(states)
ok = 0; act = 0
for st in states:
    j = res.get(st["name"])
    if not j or j["outcome"] != "returned":
        print(st["name"], "no result", (j or {}).get("outcome")); continue
    ran = any(a == 0x1EEAF for a, o, n in j["mem"])
    pred = predict(*st["_p"])
    ok += (ran == pred); act += pred
    if ran != pred: print("MISMATCH", st["name"], st["_p"], "pred", pred, "ran", ran)
print("window prediction MATCH %d / %d (%d inside the window, %d outside)" % (ok, len(states), act, len(states) - act))
