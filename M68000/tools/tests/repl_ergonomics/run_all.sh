#!/bin/bash
# Runs every test here against one build; with a second (base) build also runs the NOTRACE identity
# check base-vs-this. Exit 1 when any test fails.
# usage: run_all.sh [dll] [base.dll]
d=$(cd "$(dirname "$0")" && pwd)
dll=${1:-bin/Debug/net8.0/M68000.dll}
rc=0
for t in t1_trace_default t2_watch_len_and_errors t3_wb_ww t5_gemdos_junk_a7; do
    echo "===== $t"; bash "$d/$t.sh" "$dll" || rc=1
done
if [ $# -ge 2 ]; then echo "===== t1_notrace_identical"; bash "$d/t1_notrace_identical.sh" "$2" "$dll" || rc=1; fi
exit $rc
