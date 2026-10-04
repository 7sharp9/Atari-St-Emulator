#!/usr/bin/env python3
"""Differential gate: btai.cd58 (level spawner) against `callcap cd58` for the live level and all
eight level files `0`..`7` (each poked over $201c8..).  usage: gate_spawn.py [snap]"""
import sys, os
from btram import *
from btharness import Harness
import btai

SNAP = sys.argv[1] if len(sys.argv) > 1 else "play_start.snap"
h = Harness(SNAP)
base = h.base
files = os.path.join(WORK, "files")
states = [dict(name="spawn_live", pokes={}, presets={}, target="cd58", steps=6000000)]
for n in "01234567":
    d = open(os.path.join(files, n), "rb").read()
    pk = {0x201C8 + i: d[i] for i in range(len(d))}
    states.append(dict(name="spawn_file%s" % n, pokes=pk, presets={}, target="cd58", steps=6000000))
res, log = h.run(states, "spawn")
ok = 0
for stt in states:
    nm = stt["name"]
    j = res.get(nm)
    if not j or j["outcome"] != "returned":
        print(nm, "no result", (j or {}).get("outcome")); continue
    ram = bytearray(base)
    for a, v in stt["pokes"].items():
        ram[a] = v
    m = btai.Mem(ram)
    btai.cd58(m)
    want = m.diff()
    sp = j["entrySP"]
    got = {a: new for a, old, new in j["mem"] if not (sp - 256 <= a < sp + 8)}
    nrec = sum(1 for i in range(btai.NACT) if m.r[0x1F020 + 16 * i])
    nobj = sum(1 for i in range(164) if m.w(btai.MOBJ + 10 * i))
    same = want == got
    print("%-14s steps %-8d changed bytes ref %d / callcap %d  actors %d  map objects %d  %s"
          % (nm, j["steps"], len(want), len(got), nrec, nobj, "MATCH" if same else "DIFF %s" % sorted(set(want) ^ set(got))[:5]))
    ok += same
print("MATCH %d / %d" % (ok, len(states)))
