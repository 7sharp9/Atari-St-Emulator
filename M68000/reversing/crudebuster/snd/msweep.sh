#!/bin/sh
# msweep.sh <name> [env...]: run lua/sweep.lua headless (own CB_RUN per name so parallel sweeps do not share state files)
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../../../.." && pwd)
name=$1; shift
export SND_DIR=$here CB_RUN=$here/run_$name LOG=$here/out/$name.log
mkdir -p "$CB_RUN"
for kv in "$@"; do export "$kv"; done
exec "$root/reversing/crudebuster/cbmame.sh" run "$here/lua/sweep.lua" ${SECS:-3000}
