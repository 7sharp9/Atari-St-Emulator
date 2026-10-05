#!/bin/sh
# par.sh <name> VAR=value ... : one dm.lua run in its own copy of the run directory ($PAR_RUNS/run_<name>, states copied from $PAR_SRC/sta/ffightuc),
# log $PAR_OUT/<name>.log, stdout <name>.out. Two runs at once never share cfg/nvram/state files. Arguments of the form VAR=value override the defaults (DM_OUT, DM_LOG).
# Defaults: PAR_ROOT = scratchpad/finalfight/boss (PAR_RUNS = PAR_ROOT/runs, PAR_OUT = PAR_ROOT/out, PAR_SRC = PAR_ROOT/run).
here=$(cd "$(dirname "$0")" && pwd)
root=${M68000_ROOT:-$(cd "$here/../../../.." && pwd)}
PAR_ROOT=${PAR_ROOT:-$root/scratchpad/finalfight/boss}
PAR_RUNS=${PAR_RUNS:-$PAR_ROOT/runs}; PAR_OUT=${PAR_OUT:-$PAR_ROOT/out}; PAR_SRC=${PAR_SRC:-$PAR_ROOT/run}
name=$1; shift
run="$PAR_RUNS/run_$name"
mkdir -p "$run/sta/ffightuc" "$PAR_OUT"
cp "$PAR_SRC"/sta/ffightuc/*.sta "$run/sta/ffightuc/" 2>/dev/null
env DM_RUN="$run" DM_OUT="$PAR_OUT" DM_LOG="$PAR_OUT/$name.log" "$@" sh "$here/mame.sh" "$here/dm.lua" > "$PAR_OUT/$name.out" 2>&1
