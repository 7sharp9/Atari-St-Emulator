#!/bin/sh
# mrun.sh <name> [env assignments...] : run lua/run.lua headless with this agent's CB_RUN, log to out/<name>.log
# e.g. ./mrun.sh play1 CB_PLAN=$PWD/../../../../reversing/crudebuster/lua/plans/play1.lua CB_STOP=2500
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../../../.." && pwd)
name=$1; shift
mkdir -p "$here/run_$name"; export SND_DIR=$here CB_DIR=$root/reversing/crudebuster/lua CB_RUN=$here/run_$name LOG=$here/out/$name.log
for kv in "$@"; do export "$kv"; done
exec "$root/reversing/crudebuster/cbmame.sh" run "$here/lua/run.lua" ${SECS:-600}
