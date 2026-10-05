#!/bin/sh
# run.sh <name> <lua> [env...]  : MAME run with own run dir l5b/run/<name>, output to l5b/out/<name>
# (mode via MODE=run|script, default run)
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
name=$1; lua=$2; shift 2
mkdir -p "$here/out/$name" "$here/run/$name"
export CB_DIR=$root/reversing/crudebuster/lua CB_OUT=$here/out/$name CB_RUN=$here/run/$name
env "$@" "$root/reversing/crudebuster/cbmame.sh" ${MODE:-run} "$lua" ${SECS:-600} >"$here/out/$name/mame.log" 2>&1
