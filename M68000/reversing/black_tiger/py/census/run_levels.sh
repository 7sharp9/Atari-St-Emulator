#!/bin/bash
# Code census of Black Tiger per level: README.md (this directory) says what it measures and how to read it.
# usage: run_levels.sh [jobs=6] [walk_chunks=30] [idle_chunks=10] [boss_chunks=10]
# Writes scratchpad/black_tiger/census/<run>/ (chunk_NNN.npz, meta.jsonl) for runs L<k>_walk, L<k>_idle, B<k>_walk.
# LABELLED POKE: each 1M-step chunk first writes lives $1f00c = 5, so no run reaches game over and the attract demo.
HERE="$(cd "$(dirname "$0")" && pwd)"
d="$HERE"; while [ ! -f "$d/tools/rdis.py" ]; do d="$(dirname "$d")"; [ "$d" = / ] && exit 9; done
ROOT="${M68000_ROOT:-$d}"
WORK="${BT_WORK:-$ROOT/scratchpad/black_tiger}"
OUT="$WORK/census"; S="$WORK/agents/systems"
J="${1:-6}"; NW="${2:-30}"; NI="${3:-10}"; NB="${4:-10}"
mkdir -p "$OUT"
jobs_list() {
  for k in 0 1 2 3 4 5 6 7; do
    if [ $k = 0 ]; then snap="$WORK/play_start.snap"; else snap="$S/lvl$k.snap"; fi
    echo "L${k}_walk $snap walk $NW"
    echo "L${k}_idle $snap idle $NI"
    echo "B${k}_walk $S/boss/boss${k}_fight.snap walk $NB"
  done
}
jobs_list | xargs -P "$J" -L 1 bash -c '
  run="$0"; snap="$1"; frag="$2"; n="$3"
  rm -rf "'"$OUT"'/$run"
  "'"$ROOT"'/.venv/bin/python" "'"$ROOT"'/tools/code_census.py" run "$snap" "'"$OUT"'/$run" --chunks "$n" \
    --per-chunk "'"$HERE"'/$frag.txt" --disk-a "'"$WORK"'/bt_auto.st" \
    --read 17846:2 --read 1f00c:2 --read 1f010:1 --stop-if-changed 17846:2 > "'"$OUT"'/$run.log" 2>&1
  echo "$run rc=$? $(tail -1 "'"$OUT"'/$run.log")"'
