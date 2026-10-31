#!/usr/bin/env python3
"""Fight a boss for real from boss<L>_fight.snap: joystick-1 input only, no pokes.

Policy, one IKBD packet per HOLD steps (default 60,000 = one 5-VBL game frame): ring distance dx from the hero
($1f014) to the first live boss record ($1f020, $1f030, ...; the level is a ring of width $1effe); |dx| < 20 walk
away, |dx| > 52 or facing away ($1f013) walk toward, otherwise alternate fire ($80) and release (0). Weapon reach
is 16*$1781e px in front of the hero ($e930), contact damage needs 16 px ($e016), so the hero swings from 20..52 px.

Signals (stserver write watches on the boss records, writer PC from the event):
  $e9b2  weapon hit inside $e930 (hp -= 2*weapon+1)       $e6c2  knife hit ($e6b0 -> $10a10, hp -= 1)
  $1f020 type byte cleared = boss slot empty                $c656 / $1025c  level clear test passed / bonus paid
After the bonus it renders RENDER_AFTER more frames, presses SPACE at the disk prompt and runs until the level
index $17846 changes.
Output: $BT_WORK/agents/bossfight/L<L>/: fight.log, frames/f<NNN>.png, kill.snap (first chunk with the boss slot
empty), prompt.snap, next_level.snap.
usage (from M68000/): boss_fight.py [L=0] [chunks=400] [hold=60000]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from btram import ROOT, WORK
from stclient import StServer

L = int(sys.argv[1]) if len(sys.argv) > 1 else 0
CHUNKS = int(sys.argv[2]) if len(sys.argv) > 2 else 400
HOLD = int(sys.argv[3]) if len(sys.argv) > 3 else 60000
RENDER_AFTER = 40
out = os.path.join(WORK, "agents", "bossfight", "L%d" % L); os.makedirs(os.path.join(out, "frames"), exist_ok=True)
log = open(os.path.join(out, "fight.log"), "w")
def say(*a):
    print(*a, file=log, flush=True); print(*a, flush=True)

s = StServer(ROOT)
s("load", snapshot=os.path.join(WORK, "agents", "systems", "boss", "boss%d_fight.snap" % L), disk=os.path.join(WORK, "bt_auto.st"))
ring = int.from_bytes(s.read(0x1EFFE, 2), "big")
NREC = 4
hp_w = s("watch_add", lo=0x1F020, hi=0x1F020 + 16 * NREC - 1, kind="w", source="cpu")["id"]
A = [0x101B0, 0xC656, 0x1025C, 0xD44A]
tot = dict.fromkeys(A, 0)
pcs = {}
fire = False
kill_chunk = bonus_chunk = None

def stats():
    r = s.read(0x1F000, 16 + 16 * (NREC + 1))
    return r

def drain():
    """Fold this chunk's record writes into per-PC counts; return the hp/type events worth printing."""
    ev = s("watch_events", id=hp_w)[0]
    if ev["dropped"]: say("WARNING dropped", ev["dropped"])
    shown = []
    for e in ev["events"]:
        a = int(e["addr"].lstrip("$"), 16); off = (a - 0x1F020) % 16; rec = (a - 0x1F020) // 16 + 1
        if off == 8 or (off == 0 and e["width"] == 1):
            key = (e["pc"], "hp" if off == 8 else "type")
            pcs[key] = pcs.get(key, 0) + 1
            shown.append("r%d.%s=%s@%s" % (rec, key[1], e["value"], e["pc"]))
    return shown

for i in range(CHUNKS):
    r = stats(); hx = int.from_bytes(r[0x14:0x16], "big")
    live = [r[16 * k:16 * k + 16] for k in range(2, 2 + NREC) if r[16 * k]]
    if not r[0x10]:
        say("hero dead at chunk", i); break
    if live:
        bx = int.from_bytes(live[0][4:6], "big"); dx = ((bx - hx + ring // 2) % ring) - ring // 2
        face_ok = (dx > 0) == (r[0x13] == 0)
        if abs(dx) < 20: st = 0x04 if dx > 0 else 0x08; fire = False
        elif abs(dx) > 52 or not face_ok: st = 0x08 if dx > 0 else 0x04; fire = False
        else: fire = not fire; st = 0x80 if fire else 0
    else:
        dx = None; st = 0
    s("kbd", bytes=["ff", "%02x" % st])
    h = s("hits", steps=HOLD, addrs=A)
    c = {int(x["addr"].lstrip("$"), 16): x["count"] for x in h["hits"]}
    for k in A: tot[k] += c[k]
    shown = drain()
    s("render", path=os.path.join(out, "frames", "f%03d.png" % i))
    r2 = stats()
    say("%3d st %02x dx %5s hero %s recs %s armour %d vit %d money %d | %s%s" % (
        i, st, dx, r2[0x10:0x18].hex(" "), " ".join(r2[16 * k:16 * k + 9].hex() for k in range(2, 2 + NREC)),
        r2[7], r2[0xF], int.from_bytes(r2[2:4], "big"), " ".join(shown),
        "".join(" %x:%d" % (k, c[k]) for k in (0xC656, 0x1025C, 0xD44A) if c[k])))
    if kill_chunk is None and r2[0x20] == 0:
        kill_chunk = i; s("save", path=os.path.join(out, "kill.snap"))
    if bonus_chunk is None and c[0x1025C]:
        bonus_chunk = i
    if bonus_chunk is not None and i >= bonus_chunk + RENDER_AFTER:
        break

say("totals", {hex(k): v for k, v in tot.items()})
say("record writes by (pc, field):", {"%s %s" % k: v for k, v in sorted(pcs.items())})
say("kill chunk", kill_chunk, "bonus chunk", bonus_chunk)
if bonus_chunk is not None:
    s("save", path=os.path.join(out, "prompt.snap"))
    lvl0 = int.from_bytes(s.read(0x17846, 2), "big")
    s("kbd", bytes=["39"]); s("step", n=HOLD); s("kbd", bytes=["b9"])
    for j in range(100):
        s("step", n=HOLD)
        lvl = int.from_bytes(s.read(0x17846, 2), "big")
        if lvl != lvl0: break
    s("step", n=3000000)
    r = stats()
    say("after SPACE: level index %d -> %d after %d chunks, hero %s, money %d, $1eeb8 %s" % (
        lvl0, lvl, j + 1, r[0x10:0x18].hex(" "), int.from_bytes(r[2:4], "big"), s.read(0x1EEB8, 2).hex()))
    s("save", path=os.path.join(out, "next_level.snap")); s("render", path=os.path.join(out, "next_level.png"))
s.close()
