"""Call and interrupt census of an ATARI_TRACE_EVENTS log: every call target (kind 3) and
interrupt target (kind 6) with its count. Routines called once per game tick share one count,
which picks out a main loop's body; the interrupt line names the live handlers and their rates.

usage: uv run python tools/call_census.py <events.bin> [min_count]

Make the log over a whole number of VBLs (12,000 steps each), e.g. 200 VBLs from a snapshot:
    echo 's 2400000' | ATARI_TRACE_EVENTS=ev.bin dotnet exec bin/Debug/net8.0/M68000.dll resume <snap> repl
Worked example: reversing/populous2/README.md "Main loop" (23 targets at 29 calls in 200 VBLs).
Reads the log through trace_cfg.load.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trace_cfg  # noqa: E402


def census(path):
    _, _, recs = trace_cfg.load(path)
    calls, ints = collections.Counter(), collections.Counter()
    for _sc, _pc, tg, _op, kind in recs:
        if kind == 3:
            calls[tg & 0xFFFFFF] += 1
        elif kind == 6:
            ints[tg & 0xFFFFFF] += 1
    return recs, calls, ints


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    lo = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    recs, calls, ints = census(sys.argv[1])
    if not recs:
        sys.exit(f"{sys.argv[1]}: no records")
    print(f"records {len(recs)} steps {recs[0][0]}..{recs[-1][0]}")
    print("interrupt targets", " ".join(f"${t:06x}:{n}" for t, n in ints.most_common()))
    for t, n in sorted(calls.items()):
        if n >= lo:
            print(f"{t:06x} {n:6d}")


if __name__ == "__main__":
    main()
