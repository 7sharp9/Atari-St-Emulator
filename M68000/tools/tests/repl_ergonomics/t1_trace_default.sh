#!/bin/bash
# Change 1: the per-instruction trace is opt-in. With neither ATARI_TRACE nor ATARI_NOTRACE set, a
# 200,000-step cold boot prints no trace lines and almost nothing on stdout; ATARI_TRACE=1 prints a
# `$xxxxxx: ` line per instruction (the positive control); ATARI_NOTRACE wins over ATARI_TRACE.
# usage: t1_trace_default.sh [dll]
. "$(dirname "$0")/common.sh"
trace_lines() { grep -c -E '^\$[0-9a-f]{6}: ' "$1"; }

env -u ATARI_NOTRACE -u ATARI_TRACE dotnet exec "$DLL" 200000 > "$OUT/none.out" 2> "$OUT/none.err"
n_none=$(trace_lines "$OUT/none.out"); sz_none=$(wc -c < "$OUT/none.out" | tr -d ' ')
echo "neither variable, 200000 steps: stdout $sz_none bytes, $n_none trace lines; head:"; head -c 300 "$OUT/none.out"; echo

env -u ATARI_NOTRACE ATARI_TRACE=1 dotnet exec "$DLL" 2000 > "$OUT/on.out" 2> "$OUT/on.err"
n_on=$(trace_lines "$OUT/on.out")
echo "ATARI_TRACE=1, 2000 steps: $n_on trace lines; head:"; head -3 "$OUT/on.out"

ATARI_TRACE=1 ATARI_NOTRACE=1 dotnet exec "$DLL" 2000 > "$OUT/both.out" 2> "$OUT/both.err"
n_both=$(trace_lines "$OUT/both.out"); sz_both=$(wc -c < "$OUT/both.out" | tr -d ' ')
echo "ATARI_TRACE=1 ATARI_NOTRACE=1, 2000 steps: stdout $sz_both bytes, $n_both trace lines"

check "no trace lines with neither variable" [ "$n_none" -eq 0 ]
check "stdout under 4096 bytes with neither variable" [ "$sz_none" -lt 4096 ]
check "ATARI_TRACE=1 prints >= 1000 trace lines for 2000 steps" [ "$n_on" -ge 1000 ]
check "ATARI_NOTRACE wins over ATARI_TRACE" [ "$n_both" -eq 0 ]
finish
