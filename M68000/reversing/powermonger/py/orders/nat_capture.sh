#!/usr/bin/env bash
# nat_capture.sh <name> <entry-addr> <start.snap> <clicks.py tokens...>
# Resumes <start.snap>, plays the clicks (reversing/powermonger/py/clicks.py), stops at the first natural entry of <entry-addr>
# and writes nat/<name>_1.snap/.ram/.json (tools/capture_hits.py; the json holds the entry registers).
set -e
cd "$(dirname "$0")/../../../.."
n=$1; addr=$2; snap=$3; shift 3
WORK=${WORK:-scratchpad/pm141/agents/orders}
out=$WORK/nat
args=()
# the last click's trailing "mouse move 0 0 / s 300000" is dropped: the executor runs inside it
while IFS= read -r l; do args+=(--pre "$l"); done < <(python3 reversing/powermonger/py/clicks.py "$@" | python3 -c "import sys; l=sys.stdin.read().splitlines(); print(chr(10).join(l[:-2]))")
.venv/bin/python tools/capture_hits.py "$snap" "$addr" 1 "$out" --name "$n" --max 30000000 "${args[@]}"
