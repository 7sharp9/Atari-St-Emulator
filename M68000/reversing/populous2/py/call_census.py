"""Call and interrupt census of an ATARI_TRACE_EVENTS log: every call target (kind 3) and
interrupt target (kind 6) with its count, which picks out the once-per-tick routines.

usage: uv run python reversing/populous2/py/call_census.py <events.bin> [min_count]
e.g. the main-loop census of README "Main loop": 2.4M steps from p2_game_60m,
    ATARI_TRACE_EVENTS=ev60.bin dotnet exec bin/Debug/net8.0/M68000.dll resume p2_game_60m.snap repl  (stdin: s 2400000)
"""
import collections, os, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, "tools", "rdis.py")):
    d = os.path.dirname(d)
sys.path.insert(0, os.path.join(os.environ.get("M68000_ROOT", d), "tools"))
import trace_cfg  # noqa: E402

_, _, recs = trace_cfg.load(sys.argv[1])
lo = int(sys.argv[2]) if len(sys.argv) > 2 else 1
calls, ints = collections.Counter(), collections.Counter()
for sc, pc, tg, op, k in recs:
    if k == 3:
        calls[tg & 0xFFFFFF] += 1
    elif k == 6:
        ints[tg & 0xFFFFFF] += 1
print(f"records {len(recs)} steps {recs[0][0]}..{recs[-1][0]}")
print("interrupt targets", " ".join(f"${t:06x}:{n}" for t, n in ints.most_common()))
for t, n in sorted(calls.items()):
    if n >= lo:
        print(f"{t:06x} {n:6d}")
