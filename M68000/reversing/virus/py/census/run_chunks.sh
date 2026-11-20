#!/bin/bash
# usage: run_chunks.sh <label> <start.snap> <nchunks> <chunk_steps> [disk-arg...]
# Runs the REPL from <start.snap> in chunk_steps pieces with ATARI_TRACE_EVENTS on, reduces each log
# with reduce_evt.py, deletes the log, and appends one JSON line per chunk (wave $32a50, lives $32a54
# at start and end) to $CENSUS_DIR (default $VIRUS_WORK/census, i.e. scratchpad/virus/census)/meta.jsonl. Chunks chain through a rolling snapshot.
HERE="$(cd "$(dirname "$0")" && pwd)"
d="$HERE"; while [ ! -f "$d/tools/rdis.py" ]; do d="$(dirname "$d")"; [ "$d" = / ] && exit 9; done
ROOT="$d"
WORK="${CENSUS_DIR:-${VIRUS_WORK:-$ROOT/scratchpad/virus}/census}"
label="$1"; snap="$2"; n="$3"; steps="$4"
mkdir -p "$WORK/$label"
cd "$ROOT"
cur="$snap"
for ((i=0;i<n;i++)); do
  tag=$(printf '%s_%03d' "$label" $i)
  out=$(printf 'm 32a50 2\nm 32a54 2\ns %d\nm 32a50 2\nm 32a54 2\nm 62a5f 1\nsnap %s\nq\n' "$steps" "$WORK/roll_$label.snap.new" \
    | ATARI_TRACE_EVENTS="$WORK/$tag.evt" dotnet exec bin/Debug/net8.0/M68000.dll resume "$cur" repl 2>&1)
  [ -f "$WORK/roll_$label.snap.new" ] || { echo "$out" | tail -5; echo "chunk $tag failed"; exit 1; }
  mv "$WORK/roll_$label.snap.new" "$WORK/roll_$label.snap"
  [ -f "$WORK/roll_$label.snap.new.prov.json" ] && mv "$WORK/roll_$label.snap.new.prov.json" "$WORK/roll_$label.snap.prov.json"
  cur="$WORK/roll_$label.snap"
  nums=$(echo "$out" | grep -E '^[0-9a-f]{2}( [0-9a-f]{2})*$' | tr '\n' ' ')
  .venv/bin/python "$HERE/reduce_evt.py" "$WORK/$tag.evt" "$WORK/$label/$tag.npz" > /dev/null || exit 1
  rm -f "$WORK/$tag.evt"
  echo "{\"label\":\"$label\",\"chunk\":$i,\"steps\":$steps,\"mem\":\"$nums\"}" >> "$WORK/meta.jsonl"
  echo "$tag: $nums"
done
