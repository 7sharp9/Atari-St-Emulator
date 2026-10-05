#!/bin/sh
# mscript.sh <lua> <name> [env...]: run a debugger-mode (-debug -debugger none) script with this agent's run dir; LOG=out/<name>.log
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../../../.." && pwd)
lua=$1; name=$2; shift; shift
export SND_DIR=$here CB_DIR=$root/reversing/crudebuster/lua CB_RUN=$here/run_$name LOG=$here/out/$name.log
mkdir -p "$CB_RUN"
for kv in "$@"; do export "$kv"; done
exec "$root/reversing/crudebuster/cbmame.sh" script "$here/lua/$lua" ${SECS:-3000}
