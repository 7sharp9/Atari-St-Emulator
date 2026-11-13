#!/bin/bash
# Change 5: ATARI_TRACE_GEMDOS=1 survives a `trap #1` executed with a junk A7, and does not change the
# run. Synthetic version of Captive's TOS bomb loop: 5M steps into a cold boot, the VBL vector ($70)
# is pointed at RAM code `movea.l #<junk>,a7 / trap #1`; the next VBL runs it. Two junk values: an
# unmapped address ($4261ec, the one Captive's bomb loop had) and an odd RAM address ($15f7). For
# each the final registers must match a run without ATARI_TRACE_GEMDOS.
# usage: t5_gemdos_junk_a7.sh [dll]
. "$(dirname "$0")/common.sh"
run() { # run <a7 hex, 8 digits> <tag> [env...]
    local a7=$1 tag=$2; shift 2
    printf 's 5000000\nw 10000 2e7c%s\nw 10004 %s4e41\nw 70 00010000\ns 30000\nr\nq\n' "${a7:0:4}" "${a7:4:4}" \
        | env "$@" dotnet exec "$DLL" 1 repl > "$OUT/$tag.out" 2> "$OUT/$tag.err"
    echo "$tag: exit $? ; stdout $(wc -l < "$OUT/$tag.out" | tr -d ' ') lines"
}
for a7 in 004261ec 000015f7; do
    run $a7 trace_$a7 ATARI_NOTRACE=1 ATARI_TRACE_GEMDOS=1
    run $a7 plain_$a7 ATARI_NOTRACE=1
    echo "--- trace_$a7 stderr: lines other than GEMDOS_CALL with a readable func, and the last 3 lines"
    grep -v -E '^GEMDOS_CALL pc=\$[0-9a-f]{8} func=\$[0-9a-f]{4}$' "$OUT/trace_$a7.err" | head -12
    tail -3 "$OUT/trace_$a7.err"
    echo "--- trace_$a7 final PC/A7: $(grep -E '^PC:|A7:' "$OUT/trace_$a7.out" | tr '\n' ' ')"
    check "A7=\$$a7: no unhandled exception under ATARI_TRACE_GEMDOS" \
        bash -c "! grep -q 'Unhandled exception' '$OUT/trace_$a7.err'"
    check "A7=\$$a7: the REPL reached its final r (registers printed)" grep -q '^PC:' "$OUT/trace_$a7.out"
    check "A7=\$$a7: same final state with and without ATARI_TRACE_GEMDOS" cmp "$OUT/trace_$a7.out" "$OUT/plain_$a7.out"
done
check "the junk-A7 trap #1 was logged as func=???? (the trace saw it)" grep -q -F 'func=????' "$OUT/trace_004261ec.err"
finish
