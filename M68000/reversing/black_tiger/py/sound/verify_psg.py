"""Gate: predicted PSG volume writes vs the emulator's live PSG register writes.

For each sound id the script
  1. resumes a snapshot (default play_start.snap) in the REPL,
  2. optionally pokes the pending-sound word `$17848` (id 1..8; LABELLED POKE, the game's own
     request cell, consumed by the frame driver at $c956/$cc62 -> $105e8) or, with --natural,
     injects nothing and just runs (use a snapshot where the game requests the sound itself),
  3. `watch ff8800 8` and runs enough steps for the stream to finish,
  4. reads the WATCH lines (stderr) and groups them into ticks: one tick = a movep.l to $ff8800
     (R8<-A, R9<-B, 4 byte writes) followed by a movep.w (R10<-C), all from PC $0106f6/$0106fc,
  5. compares the (A,B,C) sequence with btsnd.predict_regs(id).

Prints per id: ticks captured, ticks predicted, exact matches (aligned at the first tick), and the
register-select bytes seen (must be 8,9,8?,... as per the table: 08 09 0a).

Usage: verify_psg.py [--snap path] [--ids 1,2,3] [--natural] [--steps-per-tick 187]
Needs ATARI_NOTRACE=1 (set here) and the existing M68000.dll; never builds.
"""
import argparse
import os
import re
import subprocess
import sys

from btsnd import BT_WORK, ROOT, OUT, load_tables, predict_regs, stream
from btsnd_common import Snap

DLL = os.path.join(ROOT, "bin", "Debug", "net8.0", "M68000.dll")
DISK = os.path.join(BT_WORK, "bt_auto.st")
WATCH = re.compile(r"WATCH: step=(\d+) pc=\$([0-9a-f]+) WriteByte \$00ff88(0[0-7]) <- \$([0-9a-f]+)")


def run_repl(snap, script, tag):
    os.makedirs(os.path.join(OUT, "run"), exist_ok=True)
    sp = os.path.join(OUT, "run", tag + ".repl")
    open(sp, "w").write(script)
    env = dict(os.environ, ATARI_NOTRACE="1")
    p = subprocess.run(["dotnet", "exec", DLL, "resume", os.path.abspath(snap), "repl", "--disk-a", DISK],
                       stdin=open(sp), capture_output=True, text=True, cwd=ROOT, env=env)
    open(os.path.join(OUT, "run", tag + ".out"), "w").write(p.stdout + "\n" + p.stderr)
    return p.stdout, p.stderr


def ticks_from_log(err):
    """Group Timer A handler PSG writes into (step, A, B, C) tuples."""
    ev = [(int(m.group(1)), int(m.group(2), 16), int(m.group(3), 16), int(m.group(4), 16))
          for m in WATCH.finditer(err)]
    ev = [e for e in ev if e[1] in (0x106f6, 0x106fc)]
    ticks, cur, sel = [], {}, {}
    i = 0
    while i < len(ev):
        step = ev[i][0]
        grp = [e for e in ev[i:i + 8] if e[0] == step or e[0] == step + 2]
        # movep.l = steps s: 8800<-8, 8802<-A, 8804<-9, 8806<-B ; movep.w = s+2: 8800<-a, 8802<-C
        l = [e for e in grp if e[1] == 0x106f6]
        w = [e for e in grp if e[1] == 0x106fc]
        if len(l) == 4 and len(w) == 2:
            val = {e[2]: e[3] for e in l}
            ticks.append((step, val[2], val[6], w[1][3], (l[0][3], l[2][3], w[0][3])))
        i += len(grp)
    return ticks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap", default=os.path.join(BT_WORK, "play_start.snap"))
    ap.add_argument("--ids", default="1,2,3,4,5,6,7,8")
    ap.add_argument("--natural", action="store_true")
    ap.add_argument("--steps-per-tick", type=int, default=187)
    ap.add_argument("--extra", type=int, default=40000)
    a = ap.parse_args()
    vt, rates = load_tables()
    tot_ok = tot_n = 0
    for sid in [int(x) for x in a.ids.split(",")]:
        pred = predict_regs(sid, vt)
        steps = (len(pred) + 20) * a.steps_per_tick + a.extra
        script = ("" if a.natural else "w 17848 %08x\n" % sid) + "watch ff8800 8\ns %d\nq\n" % steps
        out, err = run_repl(a.snap, script, "verify_id%d" % sid)
        ticks = ticks_from_log(err)
        got = [(t[1], t[2], t[3]) for t in ticks]
        sels = {t[4] for t in ticks}
        n = min(len(got), len(pred))
        ok = sum(1 for i in range(n) if got[i] == pred[i])
        print("id %d: captured %d ticks, predicted %d, exact match %d/%d, selects %s, first mismatch %s" % (
            sid, len(got), len(pred), ok, n, sorted(sels),
            next((i for i in range(n) if got[i] != pred[i]), None)))
        tot_ok += ok
        tot_n += n
    print("TOTAL %d/%d" % (tot_ok, tot_n))


if __name__ == "__main__":
    main()
