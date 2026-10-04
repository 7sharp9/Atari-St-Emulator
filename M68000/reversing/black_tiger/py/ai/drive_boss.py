#!/usr/bin/env python3
"""Reach each level's boss by poking the hero record onto the level-exit object (map object kind $20,
positions from the mechanics agent's special_items.txt, here re-derived from the level files with
btai.cd58) and running STEPS emulator steps.  LABELLED POKE: `w 1f014 <x><y>` (hero x.w/y.w).
Output: $BT_WORK/agents/ai/boss/boss<N>.snap (level index N) and a printed table of the boss records.
Level index 0 starts from play_start.snap, 1..7 from agents/systems/lvl<N>.snap.
usage: drive_boss.py [steps=250000]"""
import os, subprocess, sys
from btram import *
import btai

STEPS = int(sys.argv[1]) if len(sys.argv) > 1 else 250000
outdir = os.path.join(OUT, "boss"); os.makedirs(outdir, exist_ok=True)
base = load("play_start.snap")
rows = []
for n in range(8):
    d = open(os.path.join(WORK, "files", str(n)), "rb").read()
    ram = bytearray(base); ram[0x201C8:0x201C8 + len(d)] = d
    for k in range(0x1F020, 0x1F020 + 16 * 179): ram[k] = 0
    m = btai.Mem(ram); btai.cd58(m)
    ex = [(m.w(btai.MOBJ + 10 * i + 2), m.w(btai.MOBJ + 10 * i + 4)) for i in range(164) if m.w(btai.MOBJ + 10 * i) == 0x20]
    assert len(ex) == 1
    x, y = ex[0]
    snap = "play_start.snap" if n == 0 else os.path.join("agents", "systems", "lvl%d.snap" % n)
    out = os.path.join(outdir, "boss%d.snap" % n)
    # LABELLED POKES: hero x:y, and the camera ($1efec scroll x:y, $1eff0 = y) so that the boss records are not
    # clamped to the old camera by the `scrolly+$21` rule at $e7b4..$e7c0 (the camera only ratchets upward
    # while $17832 == 0).
    s0 = load(os.path.join(WORK, snap))
    sx = ((x - 0x80) % w(s0, 0x1EFFE)) & 0xFFF8
    sy = max(0, y - 0x78)
    script = "w 1efec %04x%04x\nw 1eff0 %04x%04x\nw 1f014 %04x%04x\ns %d\nsnap %s\nq\n" % (
        sx, sy, y, w(s0, 0x1EFF2), x, y, STEPS, os.path.relpath(out, ROOT))
    p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", os.path.relpath(os.path.join(WORK, snap), ROOT),
                        "repl", "--disk-a", os.path.relpath(os.path.join(WORK, "bt_auto.st"), ROOT)],
                       input=script, capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE="1"))
    r = load(out)
    recs = [(a, r[a], r[a + 1], w(r, a + 4), w(r, a + 6), r[a + 8]) for a in range(0x1F020, 0x1F020 + 16 * 6, 16) if r[a]]
    print("level %d exit (%d,%d) flag $1eeb8=%d lvl=%d boss records: %s" % (n, x, y, w(r, 0x1EEB8), w(r, 0x17846),
          " ".join("%05x:t%d/s%d/(%d,%d)/hp%d" % q for q in recs)))
