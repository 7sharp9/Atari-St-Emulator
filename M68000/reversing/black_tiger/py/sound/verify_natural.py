"""Natural-run gate: no pokes.  Run a snapshot (optionally with joystick packets) for N steps with
`watch ff8800 8`, turn the PSG write log into a tick stream (see verify_psg.ticks_from_log) and
explain every tick with the decoder's streams.

Segmentation: at each position the tick stream is matched against the start of every sound
(ids 0..8, music id 0 included), the longest common prefix wins.  A segment that ends before
the stream's end was interrupted by a newer request (the driver has one voice, $105e8 simply
restarts).  The first segment may begin mid-stream (snapshot taken while a sound plays); that
case is searched at any offset.

Usage: verify_natural.py <snap> <steps> [--script extra-repl-lines-file] [--tag name]
Prints one line per segment and the coverage (explained ticks / ticks).
"""
import argparse
import os
import sys

from btsnd import BT_WORK, OUT, load_tables, predict_regs
from verify_psg import run_repl, ticks_from_log


def lcp(a, b, ai, bi=0):
    n = 0
    while ai + n < len(a) and bi + n < len(b) and a[ai + n] == b[bi + n]:
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snap")
    ap.add_argument("steps", type=int)
    ap.add_argument("--script", default=None, help="file of REPL lines run before the long step")
    ap.add_argument("--tag", default="natural")
    ap.add_argument("--reuse", action="store_true", help="re-analyse run/<tag>.out without re-running")
    a = ap.parse_args()
    vt, _ = load_tables()
    preds = {sid: predict_regs(sid, vt) for sid in range(9)}
    preds[100] = predict_regs(0, vt, music_overlay=True)   # id 0 with the t0 overwrite
    pre = open(a.script).read() if a.script else ""
    script = pre + "watch ff8800 8\ns %d\nq\n" % a.steps
    if a.reuse:
        err = open(os.path.join(OUT, "run", a.tag + ".out")).read()
    else:
        out, err = run_repl(a.snap, script, a.tag)
    ticks = ticks_from_log(err)
    got = [(t[1], t[2], t[3]) for t in ticks]
    steps = [t[0] for t in ticks]
    print("ticks logged:", len(got))
    p, explained, segs = 0, 0, []
    while p < len(got):
        best = (0, None, 0)
        for sid, pr in preds.items():
            n = lcp(got, pr, p)
            if n > best[0]:
                best = (n, sid, 0)
        if best[0] < 24 and p == 0:      # mid-stream start: search any offset
            for sid, pr in preds.items():
                for off in range(len(pr)):
                    n = lcp(got, pr, p, off)
                    if n > best[0]:
                        best = (n, sid, off)
        n, sid, off = best
        if n < 24:
            segs.append((steps[p], None, 0, 1, False))
            p += 1
            continue
        full = (off + n) >= len(preds[sid])
        segs.append((steps[p], sid, off, n, full))
        explained += n
        p += n
    unexplained = 0
    for s in segs:
        if s[1] is None:
            unexplained += 1
        else:
            print("step %d: id %s from tick %d, %d ticks, %s" % (
                s[0], "0 (BT4 over-written by t0 from tick 24000)" if s[1] == 100 else s[1], s[2], s[3], "ran to the end" if s[4] else "interrupted/cut off"))
    print("explained %d / %d ticks (%d unexplained)" % (explained, len(got), len(got) - explained))


if __name__ == "__main__":
    main()
